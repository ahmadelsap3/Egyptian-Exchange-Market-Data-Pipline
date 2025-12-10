#!/usr/bin/env python3
"""
Real-time stock data handler for Egyptian Exchange (EGX) using Redis buffer and TimescaleDB.

This script provides high-speed write capabilities by buffering incoming stock ticks
in Redis and batch-flushing them to TimescaleDB for persistence.

Architecture:
    1. Incoming ticks are pushed to a Redis list (buffer_tick)
    2. Periodically or on-demand, data is pulled from Redis and batch-inserted to TimescaleDB (flush_to_db)
    3. TimescaleDB hypertable ensures efficient time-series storage

Usage:
    # Setup database (one-time)
    python realtime_redis_timescaledb.py --setup-db
    
    # Buffer sample tick data
    python realtime_redis_timescaledb.py --buffer-tick COMI 45.50 1000
    
    # Flush buffered data to TimescaleDB
    python realtime_redis_timescaledb.py --flush
    
    # Run as a daemon (buffer and auto-flush)
    python realtime_redis_timescaledb.py --daemon --flush-interval 60

Environment Variables:
    REDIS_HOST: Redis server host (default: localhost)
    REDIS_PORT: Redis server port (default: 6379)
    REDIS_DB: Redis database number (default: 0)
    POSTGRES_HOST: PostgreSQL/TimescaleDB host (default: localhost)
    POSTGRES_PORT: PostgreSQL port (default: 5432)
    POSTGRES_DB: Database name (default: egx_market)
    POSTGRES_USER: Database user (default: postgres)
    POSTGRES_PASSWORD: Database password (required)
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Optional

import redis
import psycopg2
from psycopg2.extras import execute_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
LOG = logging.getLogger(__name__)

# Configuration from environment variables
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
REDIS_LIST_KEY = 'egx:ticks:buffer'

POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
POSTGRES_DB = os.environ.get('POSTGRES_DB', 'egx_market')
POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', '')


class RedisTimescaleDBHandler:
    """Handler for buffering ticks in Redis and flushing to TimescaleDB."""
    
    def __init__(self):
        """Initialize Redis and PostgreSQL connections."""
        self.redis_client = None
        self.pg_conn = None
        self._connect_redis()
        self._connect_postgres()
    
    def _connect_redis(self):
        """Connect to Redis server."""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            LOG.info(f"✓ Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            LOG.error(f"✗ Failed to connect to Redis: {e}")
            raise ConnectionError(f"Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}") from e
    
    def _connect_postgres(self):
        """Connect to PostgreSQL/TimescaleDB."""
        try:
            self.pg_conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD
            )
            self.pg_conn.autocommit = False
            LOG.info(f"✓ Connected to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        except psycopg2.Error as e:
            LOG.error(f"✗ Failed to connect to PostgreSQL: {e}")
            raise ConnectionError(f"Failed to connect to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}") from e
    
    def setup_database(self):
        """
        Create the egx_ticks table and convert it to a TimescaleDB hypertable.
        This should be run once during initial setup.
        """
        LOG.info("Setting up database schema...")
        
        cursor = self.pg_conn.cursor()
        
        try:
            # Create table if it doesn't exist
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS egx_ticks (
                time TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                volume INT NOT NULL
            );
            """
            cursor.execute(create_table_sql)
            LOG.info("✓ Table 'egx_ticks' created (or already exists)")
            
            # Create hypertable (will fail if already a hypertable, which is ok)
            try:
                hypertable_sql = """
                SELECT create_hypertable('egx_ticks', 'time', if_not_exists => TRUE);
                """
                cursor.execute(hypertable_sql)
                LOG.info("✓ Converted 'egx_ticks' to TimescaleDB hypertable")
            except psycopg2.Error as e:
                if "already a hypertable" in str(e):
                    LOG.info("✓ Table 'egx_ticks' is already a hypertable")
                    self.pg_conn.rollback()
                else:
                    raise
            
            # Create index on symbol for faster queries
            index_sql = """
            CREATE INDEX IF NOT EXISTS idx_egx_ticks_symbol 
            ON egx_ticks (symbol, time DESC);
            """
            cursor.execute(index_sql)
            LOG.info("✓ Index on (symbol, time) created")
            
            self.pg_conn.commit()
            LOG.info("✓ Database setup complete")
            
        except psycopg2.Error as e:
            self.pg_conn.rollback()
            LOG.error(f"✗ Database setup failed: {e}")
            raise
        finally:
            cursor.close()
    
    def buffer_tick(self, symbol: str, price: float, volume: int, timestamp: Optional[datetime] = None):
        """
        Buffer a stock tick into Redis for later batch insertion.
        
        Args:
            symbol: Stock symbol (e.g., 'COMI', 'ETEL')
            price: Stock price
            volume: Trading volume
            timestamp: Optional timestamp (defaults to current time)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Create tick data structure
        tick = {
            'time': timestamp.isoformat(),
            'symbol': symbol,
            'price': float(price),
            'volume': int(volume)
        }
        
        # Push to Redis list
        try:
            self.redis_client.rpush(REDIS_LIST_KEY, json.dumps(tick))
            LOG.debug(f"Buffered tick: {symbol} @ {price} (vol: {volume})")
        except redis.RedisError as e:
            LOG.error(f"Failed to buffer tick: {e}")
            raise
    
    def flush_to_db(self) -> int:
        """
        Flush all buffered ticks from Redis to TimescaleDB in a batch operation.
        Uses Redis Lua script for atomic read-and-clear operation.
        
        Returns:
            Number of records inserted
        """
        cursor = self.pg_conn.cursor()
        records_inserted = 0
        ticks = []  # Initialize to avoid UnboundLocalError
        
        try:
            # Use Lua script for atomic read-and-clear operation
            # This prevents race conditions and ensures all items are read before clearing
            lua_script = """
            local items = redis.call('LRANGE', KEYS[1], 0, -1)
            if #items > 0 then
                redis.call('DEL', KEYS[1])
            end
            return items
            """
            
            # Execute Lua script atomically
            tick_jsons = self.redis_client.eval(lua_script, 1, REDIS_LIST_KEY)
            
            if not tick_jsons:
                LOG.info("No ticks to flush")
                return 0
            
            # Parse the ticks
            ticks = []
            for tick_json in tick_jsons:
                try:
                    tick = json.loads(tick_json)
                    ticks.append(tick)
                except json.JSONDecodeError as e:
                    LOG.warning(f"Skipping invalid tick data: {e}")
                    continue
            
            if not ticks:
                LOG.info("No valid ticks to flush")
                return 0
            
            LOG.info(f"Flushing {len(ticks)} ticks to TimescaleDB...")
            
            # Batch insert using execute_batch for efficiency
            insert_sql = """
            INSERT INTO egx_ticks (time, symbol, price, volume)
            VALUES (%(time)s, %(symbol)s, %(price)s, %(volume)s);
            """
            
            execute_batch(cursor, insert_sql, ticks, page_size=1000)
            self.pg_conn.commit()
            
            records_inserted = len(ticks)
            LOG.info(f"✓ Successfully flushed {records_inserted} ticks to TimescaleDB")
            
        except psycopg2.Error as e:
            self.pg_conn.rollback()
            LOG.error(f"✗ Failed to flush to database: {e}")
            
            # Restore ticks to Redis in reverse order to maintain chronological order
            # Since we read from left (oldest first), we push back to left to maintain order
            if ticks:  # Only restore if ticks were successfully parsed
                try:
                    for tick in reversed(ticks):
                        self.redis_client.lpush(REDIS_LIST_KEY, json.dumps(tick))
                    LOG.info(f"Restored {len(ticks)} ticks back to Redis buffer")
                except redis.RedisError as redis_err:
                    LOG.critical(f"✗ Failed to restore ticks to Redis: {redis_err}")
                    LOG.critical(f"Data loss alert: {len(ticks)} ticks could not be restored")
                    # Log the lost ticks for potential recovery
                    LOG.critical(f"Lost ticks: {json.dumps(ticks)}")
            
            raise
        finally:
            cursor.close()
        
        return records_inserted
    
    def get_buffer_size(self) -> Optional[int]:
        """
        Get the current number of ticks in the Redis buffer.
        
        Returns:
            Number of ticks in buffer, or None if Redis error occurs
        """
        try:
            return self.redis_client.llen(REDIS_LIST_KEY)
        except redis.RedisError as e:
            LOG.error(f"Failed to get buffer size: {e}")
            return None
    
    def close(self):
        """Close Redis and PostgreSQL connections."""
        if self.redis_client:
            self.redis_client.close()
            LOG.info("✓ Closed Redis connection")
        
        if self.pg_conn:
            self.pg_conn.close()
            LOG.info("✓ Closed PostgreSQL connection")


def run_daemon(flush_interval: int = 60):
    """
    Run as a daemon that automatically flushes buffered data at regular intervals.
    
    Args:
        flush_interval: Seconds between automatic flushes
    """
    handler = RedisTimescaleDBHandler()
    
    LOG.info(f"Starting daemon mode (flush interval: {flush_interval}s)")
    LOG.info("Press Ctrl+C to stop")
    
    try:
        while True:
            buffer_size = handler.get_buffer_size()
            
            if buffer_size is not None and buffer_size > 0:
                LOG.info(f"Buffer size: {buffer_size} ticks")
                handler.flush_to_db()
            elif buffer_size is None:
                LOG.error("Failed to get buffer size from Redis")
            else:
                LOG.debug("Buffer is empty, waiting...")
            
            time.sleep(flush_interval)
    
    except KeyboardInterrupt:
        LOG.info("Received interrupt signal, shutting down...")
    finally:
        # Final flush before exit
        buffer_size = handler.get_buffer_size()
        if buffer_size is not None and buffer_size > 0:
            LOG.info("Performing final flush...")
            handler.flush_to_db()
        
        handler.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Real-time EGX stock data handler with Redis buffer and TimescaleDB storage"
    )
    
    parser.add_argument(
        '--setup-db',
        action='store_true',
        help='Setup database schema (run once)'
    )
    
    parser.add_argument(
        '--buffer-tick',
        nargs=3,
        metavar=('SYMBOL', 'PRICE', 'VOLUME'),
        help='Buffer a single tick (e.g., --buffer-tick COMI 45.50 1000)'
    )
    
    parser.add_argument(
        '--flush',
        action='store_true',
        help='Flush all buffered ticks to TimescaleDB'
    )
    
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run as daemon with automatic flushing'
    )
    
    parser.add_argument(
        '--flush-interval',
        type=int,
        default=60,
        help='Flush interval in seconds for daemon mode (default: 60)'
    )
    
    parser.add_argument(
        '--buffer-size',
        action='store_true',
        help='Show current buffer size'
    )
    
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Handle commands
    try:
        if args.setup_db:
            handler = RedisTimescaleDBHandler()
            handler.setup_database()
            handler.close()
        
        elif args.buffer_tick:
            symbol, price, volume = args.buffer_tick
            handler = RedisTimescaleDBHandler()
            handler.buffer_tick(symbol, float(price), int(volume))
            buffer_size = handler.get_buffer_size()
            LOG.info(f"✓ Tick buffered. Current buffer size: {buffer_size}")
            handler.close()
        
        elif args.flush:
            handler = RedisTimescaleDBHandler()
            handler.flush_to_db()
            handler.close()
        
        elif args.daemon:
            run_daemon(args.flush_interval)
        
        elif args.buffer_size:
            handler = RedisTimescaleDBHandler()
            buffer_size = handler.get_buffer_size()
            LOG.info(f"Current buffer size: {buffer_size} ticks")
            handler.close()
        
        else:
            parser.print_help()
    
    except ConnectionError as e:
        LOG.error(f"Connection failed: {e}")
        LOG.error("Please ensure Redis and PostgreSQL/TimescaleDB are running")
        sys.exit(1)
    except KeyboardInterrupt:
        LOG.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        LOG.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
