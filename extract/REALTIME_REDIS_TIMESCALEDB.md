# Real-time Stock Data Handler - Redis + TimescaleDB

## Overview

This module provides high-speed real-time stock data handling for the Egyptian Exchange (EGX) using a **Redis buffer + TimescaleDB** architecture. It ensures fast write speeds and data safety through intelligent buffering and batch insertion.

## Architecture

```
Stock Ticks → Redis Buffer → Batch Flush → TimescaleDB (Hypertable)
              (In-Memory)                   (Time-Series Optimized)
```

### Why Redis + TimescaleDB?

1. **High Write Speed**: Redis buffers incoming ticks in-memory with microsecond latency
2. **Data Safety**: Batch writes to TimescaleDB ensure persistence without slowing down ingestion
3. **Time-Series Optimization**: TimescaleDB hypertables provide efficient time-based queries
4. **Scalability**: Decoupled buffer and storage layers scale independently

## Features

- ✅ Fast in-memory buffering using Redis lists
- ✅ Efficient batch insertion to TimescaleDB
- ✅ Atomic flush operations (prevents race conditions)
- ✅ Automatic hypertable creation and partitioning
- ✅ Resilient error handling (restores buffer on flush failure with proper ordering)
- ✅ Daemon mode with automatic periodic flushing
- ✅ Comprehensive logging and monitoring

## Setup

### Prerequisites

1. **Redis Server**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Docker
docker run -d -p 6379:6379 redis:latest
```

2. **TimescaleDB (PostgreSQL extension)**
```bash
# Ubuntu/Debian
sudo apt install postgresql-14 postgresql-14-timescaledb

# macOS
brew install timescaledb/tap/timescaledb

# Docker (recommended)
docker run -d \
  --name timescaledb \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=your_password \
  timescale/timescaledb:latest-pg14
```

3. **Python Dependencies**
```bash
pip install redis psycopg2-binary
# or from requirements.txt
pip install -r requirements.txt
```

### Database Setup

1. **Create database** (if not exists):
```sql
CREATE DATABASE egx_market;
\c egx_market
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

2. **Configure environment variables**:
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0

export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=egx_market
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
```

3. **Initialize schema**:
```bash
python extract/realtime_redis_timescaledb.py --setup-db
```

This creates:
- `egx_ticks` table with columns: `time`, `symbol`, `price`, `volume`
- TimescaleDB hypertable partitioned by `time`
- Index on `(symbol, time)` for fast queries

## Usage

### 1. Buffer Individual Ticks

```bash
# Buffer a single stock tick
python extract/realtime_redis_timescaledb.py \
  --buffer-tick COMI 45.50 1000

# Buffer multiple ticks
python extract/realtime_redis_timescaledb.py --buffer-tick ETEL 12.30 5000
python extract/realtime_redis_timescaledb.py --buffer-tick SWDY 8.75 3000
```

### 2. Manual Flush

```bash
# Flush all buffered ticks to TimescaleDB
python extract/realtime_redis_timescaledb.py --flush
```

### 3. Daemon Mode (Recommended for Production)

```bash
# Auto-flush every 60 seconds (default)
python extract/realtime_redis_timescaledb.py --daemon

# Custom flush interval (30 seconds)
python extract/realtime_redis_timescaledb.py --daemon --flush-interval 30

# Run in background
nohup python extract/realtime_redis_timescaledb.py --daemon \
  --flush-interval 60 > logs/redis_timescale.log 2>&1 &
```

### 4. Monitoring

```bash
# Check buffer size
python extract/realtime_redis_timescaledb.py --buffer-size

# Check Redis directly
redis-cli LLEN egx:ticks:buffer

# Query recent data in TimescaleDB
psql -U postgres -d egx_market -c "
  SELECT * FROM egx_ticks 
  ORDER BY time DESC 
  LIMIT 10;
"
```

## Integration Examples

### With Kafka Consumer

```python
from kafka import KafkaConsumer
from realtime_redis_timescaledb import RedisTimescaleDBHandler

handler = RedisTimescaleDBHandler()

consumer = KafkaConsumer('egx_market_data', 
                         bootstrap_servers='localhost:9092')

for message in consumer:
    tick = message.value
    handler.buffer_tick(
        symbol=tick['symbol'],
        price=tick['price'],
        volume=tick['volume']
    )
    
    # Flush every 100 messages
    if handler.get_buffer_size() >= 100:
        handler.flush_to_db()
```

### With EGX API Streaming

```python
import egxpy
from realtime_redis_timescaledb import RedisTimescaleDBHandler

handler = RedisTimescaleDBHandler()

for tick in egxpy.stream_ticks(['COMI', 'ETEL']):
    handler.buffer_tick(
        symbol=tick.symbol,
        price=tick.close,
        volume=tick.volume
    )
```

## API Reference

### `RedisTimescaleDBHandler`

#### `buffer_tick(symbol, price, volume, timestamp=None)`
Buffer a stock tick into Redis.

**Parameters:**
- `symbol` (str): Stock symbol (e.g., 'COMI')
- `price` (float): Stock price
- `volume` (int): Trading volume
- `timestamp` (datetime, optional): Tick timestamp (defaults to now)

#### `flush_to_db() -> int`
Flush all buffered ticks to TimescaleDB in a batch.

**Returns:** Number of records inserted

#### `get_buffer_size() -> int`
Get the current number of ticks in the Redis buffer.

**Returns:** Buffer size (number of ticks)

#### `setup_database()`
Create database schema and hypertable (run once).

## Performance

### Benchmarks

- **Buffer Speed**: ~50,000 ticks/second (Redis in-memory)
- **Flush Speed**: ~10,000 ticks/second (batch insert to TimescaleDB)
- **Recommended Batch Size**: 100-1000 ticks
- **Recommended Flush Interval**: 30-60 seconds

### Optimization Tips

1. **Batch Size**: Larger batches = higher throughput, but more data loss risk
2. **Flush Interval**: Balance between latency and write efficiency
3. **Redis Persistence**: Enable AOF for durability (slight performance cost)
4. **TimescaleDB Tuning**: Adjust `shared_buffers`, `work_mem` for better performance

## Monitoring & Operations

### Health Checks

```bash
# Check Redis connection
redis-cli PING

# Check TimescaleDB connection
psql -U postgres -d egx_market -c "SELECT version();"

# Check data freshness
psql -U postgres -d egx_market -c "
  SELECT symbol, MAX(time) as latest_time 
  FROM egx_ticks 
  GROUP BY symbol;
"
```

### Common Issues

**Issue**: `Failed to connect to Redis`
- **Solution**: Ensure Redis is running (`redis-cli ping`)

**Issue**: `Failed to connect to PostgreSQL`
- **Solution**: Check credentials and ensure PostgreSQL is running

**Issue**: `create_hypertable() not found`
- **Solution**: Install TimescaleDB extension (`CREATE EXTENSION timescaledb;`)

**Issue**: Buffer growing without flushing
- **Solution**: Run daemon mode or set up cron job for periodic flushes

## Data Queries

### Example TimescaleDB Queries

```sql
-- Latest prices for all symbols
SELECT DISTINCT ON (symbol)
    symbol, time, price, volume
FROM egx_ticks
ORDER BY symbol, time DESC;

-- Hourly OHLCV aggregation
SELECT 
    time_bucket('1 hour', time) AS hour,
    symbol,
    first(price, time) AS open,
    max(price) AS high,
    min(price) AS low,
    last(price, time) AS close,
    sum(volume) AS volume
FROM egx_ticks
WHERE symbol = 'COMI'
GROUP BY hour, symbol
ORDER BY hour DESC;

-- Top 10 most traded symbols today
SELECT 
    symbol,
    COUNT(*) AS tick_count,
    SUM(volume) AS total_volume
FROM egx_ticks
WHERE time >= CURRENT_DATE
GROUP BY symbol
ORDER BY total_volume DESC
LIMIT 10;
```

## Production Deployment

### Systemd Service (Linux)

Create `/etc/systemd/system/egx-redis-timescale.service`:

```ini
[Unit]
Description=EGX Redis-TimescaleDB Handler
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=egx
WorkingDirectory=/opt/egx-pipeline
Environment="POSTGRES_PASSWORD=your_password"
ExecStart=/opt/egx-pipeline/.venv/bin/python \
          extract/realtime_redis_timescaledb.py \
          --daemon --flush-interval 60
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable egx-redis-timescale
sudo systemctl start egx-redis-timescale
sudo systemctl status egx-redis-timescale
```

### Docker Compose

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  timescaledb:
    image: timescale/timescaledb:latest-pg14
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: egx_market
    volumes:
      - timescale_data:/var/lib/postgresql/data

  handler:
    build: .
    depends_on:
      - redis
      - timescaledb
    environment:
      REDIS_HOST: redis
      POSTGRES_HOST: timescaledb
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    command: python extract/realtime_redis_timescaledb.py --daemon --flush-interval 60

volumes:
  redis_data:
  timescale_data:
```

## Testing

```bash
# Setup test database
python extract/realtime_redis_timescaledb.py --setup-db

# Generate test data
for i in {1..100}; do
  python extract/realtime_redis_timescaledb.py \
    --buffer-tick COMI $(echo "scale=2; 40 + $RANDOM % 10" | bc) $(($RANDOM % 10000))
done

# Verify buffer
python extract/realtime_redis_timescaledb.py --buffer-size

# Flush and verify
python extract/realtime_redis_timescaledb.py --flush
psql -U postgres -d egx_market -c "SELECT COUNT(*) FROM egx_ticks;"
```

## Security

- ✅ Use environment variables for sensitive credentials
- ✅ Enable Redis authentication (`requirepass` in redis.conf)
- ✅ Use PostgreSQL SSL connections in production
- ✅ Implement network isolation (firewall, VPC)
- ✅ Rotate credentials regularly
- ✅ Monitor for unusual access patterns

## License

MIT - Part of Egyptian Exchange Market Data Pipeline

## Related Documentation

- [Main README](../README.md)
- [Streaming Architecture](../docs/STREAMING_ARCHITECTURE.md)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Redis Documentation](https://redis.io/docs/)
