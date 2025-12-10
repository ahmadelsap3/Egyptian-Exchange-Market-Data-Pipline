#!/usr/bin/env python3
"""
Test script for Redis + TimescaleDB real-time stock data handler.

This script tests the basic functionality without requiring actual Redis
or TimescaleDB connections by using mocking.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
import sys
import os

# Add current directory to path to import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestRedisTimescaleDBHandler(unittest.TestCase):
    """Test cases for RedisTimescaleDBHandler."""
    
    @patch('realtime_redis_timescaledb.psycopg2.connect')
    @patch('realtime_redis_timescaledb.redis.Redis')
    def setUp(self, mock_redis, mock_psycopg2):
        """Set up test fixtures."""
        # Mock Redis client
        self.mock_redis_client = MagicMock()
        mock_redis.return_value = self.mock_redis_client
        
        # Mock PostgreSQL connection
        self.mock_pg_conn = MagicMock()
        mock_psycopg2.return_value = self.mock_pg_conn
        
        # Import handler after mocking
        from realtime_redis_timescaledb import RedisTimescaleDBHandler
        self.handler = RedisTimescaleDBHandler()
    
    def test_buffer_tick_basic(self):
        """Test buffering a basic tick."""
        symbol = "COMI"
        price = 45.50
        volume = 1000
        
        self.handler.buffer_tick(symbol, price, volume)
        
        # Verify rpush was called once
        self.assertEqual(self.mock_redis_client.rpush.call_count, 1)
        
        # Verify the data structure
        call_args = self.mock_redis_client.rpush.call_args
        self.assertEqual(call_args[0][0], 'egx:ticks:buffer')
        
        # Parse the JSON data
        tick_json = call_args[0][1]
        tick = json.loads(tick_json)
        
        self.assertEqual(tick['symbol'], symbol)
        self.assertEqual(tick['price'], price)
        self.assertEqual(tick['volume'], volume)
        self.assertIn('time', tick)
    
    def test_buffer_tick_with_timestamp(self):
        """Test buffering a tick with custom timestamp."""
        timestamp = datetime(2025, 12, 10, 12, 0, 0)
        
        self.handler.buffer_tick("ETEL", 12.30, 5000, timestamp)
        
        call_args = self.mock_redis_client.rpush.call_args
        tick_json = call_args[0][1]
        tick = json.loads(tick_json)
        
        self.assertEqual(tick['time'], timestamp.isoformat())
    
    def test_get_buffer_size(self):
        """Test getting buffer size."""
        self.mock_redis_client.llen.return_value = 42
        
        size = self.handler.get_buffer_size()
        
        self.assertEqual(size, 42)
        self.mock_redis_client.llen.assert_called_once_with('egx:ticks:buffer')
    
    def test_flush_to_db_empty_buffer(self):
        """Test flushing when buffer is empty."""
        self.mock_redis_client.lpop.return_value = None
        
        records_inserted = self.handler.flush_to_db()
        
        self.assertEqual(records_inserted, 0)
    
    def test_flush_to_db_with_data(self):
        """Test flushing with data in buffer."""
        # Setup mock data
        tick1 = {
            'time': '2025-12-10T12:00:00',
            'symbol': 'COMI',
            'price': 45.50,
            'volume': 1000
        }
        tick2 = {
            'time': '2025-12-10T12:01:00',
            'symbol': 'ETEL',
            'price': 12.30,
            'volume': 5000
        }
        
        # Mock lpop to return ticks then None
        self.mock_redis_client.lpop.side_effect = [
            json.dumps(tick1),
            json.dumps(tick2),
            None
        ]
        
        # Mock cursor with proper execute method
        mock_cursor = MagicMock()
        # Mock execute to return successful result
        mock_cursor.execute.return_value = None
        self.mock_pg_conn.cursor.return_value = mock_cursor
        
        # Mock execute_batch directly since it's imported from psycopg2.extras
        with patch('realtime_redis_timescaledb.execute_batch') as mock_execute_batch:
            records_inserted = self.handler.flush_to_db()
            
            self.assertEqual(records_inserted, 2)
            self.mock_pg_conn.commit.assert_called_once()
            # Verify execute_batch was called
            mock_execute_batch.assert_called_once()
    
    def test_data_validation(self):
        """Test that tick data is properly validated."""
        # Test with valid data
        self.handler.buffer_tick("COMI", 45.50, 1000)
        
        call_args = self.mock_redis_client.rpush.call_args
        tick_json = call_args[0][1]
        tick = json.loads(tick_json)
        
        # Verify types
        self.assertIsInstance(tick['symbol'], str)
        self.assertIsInstance(tick['price'], float)
        self.assertIsInstance(tick['volume'], int)
        self.assertIsInstance(tick['time'], str)
    
    def test_multiple_ticks_sequence(self):
        """Test buffering multiple ticks in sequence."""
        ticks = [
            ("COMI", 45.50, 1000),
            ("ETEL", 12.30, 5000),
            ("SWDY", 8.75, 3000)
        ]
        
        for symbol, price, volume in ticks:
            self.handler.buffer_tick(symbol, price, volume)
        
        # Verify rpush was called 3 times
        self.assertEqual(self.mock_redis_client.rpush.call_count, 3)


def run_integration_test():
    """
    Integration test that requires actual Redis and TimescaleDB.
    Run only if services are available.
    """
    print("\n" + "="*80)
    print("INTEGRATION TEST (requires Redis + TimescaleDB)")
    print("="*80)
    
    try:
        from realtime_redis_timescaledb import RedisTimescaleDBHandler
        
        print("\n1. Testing connections...")
        handler = RedisTimescaleDBHandler()
        print("   ✓ Connected to Redis and TimescaleDB")
        
        print("\n2. Testing buffer_tick...")
        handler.buffer_tick("TEST", 100.00, 1000)
        buffer_size = handler.get_buffer_size()
        print(f"   ✓ Buffered tick. Buffer size: {buffer_size}")
        
        print("\n3. Testing flush_to_db...")
        records = handler.flush_to_db()
        print(f"   ✓ Flushed {records} records to TimescaleDB")
        
        print("\n4. Cleanup...")
        handler.close()
        print("   ✓ Closed connections")
        
        print("\n" + "="*80)
        print("INTEGRATION TEST PASSED ✓")
        print("="*80)
        
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        print("\nNote: This is expected if Redis or TimescaleDB is not running.")
        print("To run integration tests, ensure both services are available.")


def main():
    """Main test runner."""
    print("="*80)
    print("Redis + TimescaleDB Handler - Test Suite")
    print("="*80)
    
    # Run unit tests
    print("\nRunning unit tests (mocked)...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRedisTimescaleDBHandler)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*80)
    if result.wasSuccessful():
        print("UNIT TESTS PASSED ✓")
    else:
        print("UNIT TESTS FAILED ✗")
    print("="*80)
    
    # Ask if user wants to run integration tests
    print("\n" + "="*80)
    print("Integration tests require running Redis and TimescaleDB instances.")
    response = input("Run integration tests? (y/N): ").strip().lower()
    
    if response == 'y':
        run_integration_test()
    else:
        print("Skipping integration tests.")


if __name__ == '__main__':
    main()
