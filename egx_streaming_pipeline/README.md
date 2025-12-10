# EGX Real-Time Streaming Pipeline

A complete real-time data pipeline for the Egyptian Stock Exchange (EGX) built with Apache Kafka, Apache Spark Structured Streaming, TimescaleDB, and Grafana.

## 📊 Architecture Overview

```
┌─────────────────┐
│  EGX Producer   │  Generate mock stock data (25 stocks + 4 indices)
│   (Python)      │  Market hours: Sun-Thu 10:00-14:30 Cairo time
└────────┬────────┘
         │ Publishes every 30 seconds
         ▼
┌─────────────────┐
│  Apache Kafka   │  Topic: egx-stock-data (3 partitions)
│  (kafka:latest) │  Port: 9092
└────────┬────────┘
         │ Consumes stream
         ▼
┌─────────────────┐
│  Apache Spark   │  Structured Streaming with Spark 3.4.1
│  Spark Job      │  - Timestamp conversion (to_timestamp)
│  (PySpark)      │  - Schema enforcement
└────────┬────────┘
         │ JDBC write
         ▼
┌─────────────────┐
│  TimescaleDB    │  PostgreSQL with TimescaleDB extension
│  (Postgres 16)  │  Database: egx_market
│                 │  Hypertable: egx_stock_prices
└────────┬────────┘
         │ Query
         ▼
┌─────────────────┐
│    Grafana      │  Real-time dashboard on port 3000
│   (v10.0.0)     │  Auto-refresh every 5 seconds
└─────────────────┘
```

## 🚀 Features

### Data Generation
- **25 Egyptian stocks** with realistic company names and tickers
- **4 market indices**: EGX30, EGX70, EGX100, EGX33 (Sharia)
- **Market hours awareness**: Generates mock data when market is closed
- **Realistic movements**: Price changes between -5% to +5%
- **Volume simulation**: Random trading volumes for stocks

### Stream Processing
- Real-time data ingestion via Kafka
- Apache Spark Structured Streaming for processing
- Automatic timestamp conversion and data validation
- Parallel processing across 3 Kafka partitions

### Data Storage
- TimescaleDB (time-series optimized PostgreSQL)
- Hypertable for efficient time-series queries
- Automatic data retention and compression

### Visualization
- Real-time Grafana dashboard
- Market status indicator (Open/Closed)
- Live stock price charts with 30-minute window
- EGX indices display with change percentages
- Top 10 Gainers & Losers tables
- Trading volume pie chart
- Market statistics (Active Stocks, Average Price, Total Volume)

## 🛠️ Tech Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Message Broker** | Apache Kafka | latest | Stream ingestion |
| **Stream Processing** | Apache Spark | 3.4.1 | Data transformation |
| **Database** | TimescaleDB | latest-pg16 | Time-series storage |
| **Visualization** | Grafana | 10.0.0 | Real-time dashboard |
| **Monitoring** | Kafka UI | latest | Kafka monitoring |
| **Database Admin** | pgAdmin | latest | Database management |
| **Language** | Python | 3.9+ | Producer & Spark job |

## 📦 Project Structure

```
egx_streaming_pipeline/
├── docker-compose.yml          # Orchestrates all services
├── producer/
│   ├── Dockerfile             # Python producer container
│   ├── egx_producer.py        # Stock data generator
│   └── requirements.txt       # Producer dependencies
├── spark-processor/
│   ├── Dockerfile             # Spark processor container
│   ├── egx_spark_job.py       # Spark Structured Streaming job
│   └── requirements.txt       # Spark job dependencies
└── grafana/
    └── dashboards/
        └── egx-live.json      # Dashboard configuration
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose installed
- At least 8GB RAM available
- Ports available: 3000, 5050, 5432, 8090, 9092

### Step 1: Start All Services

```powershell
cd egx_streaming_pipeline
docker-compose up -d
```

This starts 9 services:
1. **Kafka** - Message broker (port 9092)
2. **Kafka UI** - Kafka monitoring (port 8090)
3. **TimescaleDB** - Database (port 5432)
4. **pgAdmin** - Database admin (port 5050)
5. **Spark Master** - Spark cluster master
6. **Spark Worker** - Spark cluster worker
7. **EGX Producer** - Data generator
8. **EGX Spark Processor** - Stream processor
9. **Grafana** - Dashboard (port 3000)

### Step 2: Access Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana Dashboard | http://localhost:3000 | admin / admin |
| Kafka UI | http://localhost:8090 | None |
| pgAdmin | http://localhost:5050 | admin@admin.com / admin |

### Step 3: View Dashboard

1. Open Grafana at http://localhost:3000
2. Login with admin/admin
3. Go to Dashboards → EGX Live Market Dashboard
4. Watch real-time stock data flowing!

## 📊 Data Schema

### Kafka Message Format (JSON)
```json
{
  "ticker": "COMI",
  "company_name": "Commercial International Bank (Egypt)",
  "price": 95.25,
  "volume": 1234567,
  "price_change_percent": 2.35,
  "time": "2025-12-11T10:30:00",
  "currency": "EGP",
  "market_status": "OPEN",
  "is_mock": true
}
```

### TimescaleDB Table Schema
```sql
CREATE TABLE egx_stock_prices (
    time TIMESTAMPTZ NOT NULL,
    ticker TEXT NOT NULL,
    company_name TEXT,
    price DOUBLE PRECISION,
    volume BIGINT,
    price_change_percent DOUBLE PRECISION,
    currency TEXT,
    market_status TEXT,
    is_mock BOOLEAN
);

-- Hypertable for time-series optimization
SELECT create_hypertable('egx_stock_prices', 'time');
```

## 🔧 Configuration

### Producer Configuration (`producer/egx_producer.py`)

```python
# Market hours (Cairo timezone - EET/EEST)
MARKET_OPEN_HOUR = 10   # 10:00 AM
MARKET_CLOSE_HOUR = 14  # 2:00 PM
MARKET_CLOSE_MINUTE = 30  # 2:30 PM

# Trading days (Sunday = 0, Thursday = 4)
TRADING_DAYS = [0, 1, 2, 3, 4]  # Sun-Thu

# Data generation interval
SLEEP_INTERVAL = 30  # seconds between updates
```

### Kafka Configuration

```yaml
KAFKA_BROKER: kafka:9092
KAFKA_TOPIC: egx-stock-data
KAFKA_PARTITIONS: 3
```

### Spark Configuration

```python
# Spark Structured Streaming settings
.option("kafka.bootstrap.servers", "kafka:9092")
.option("subscribe", "egx-stock-data")
.option("startingOffsets", "earliest")
.trigger(processingTime="10 seconds")
```

## 📈 Dashboard Panels

### 1. Market Status
- Shows current market status (OPEN/CLOSED)
- Green background when open, red when closed
- Updates based on Cairo timezone

### 2. EGX Market Indices
- Displays 4 indices: EGX30, EGX70, EGX100, EGX33 Sharia
- Shows current value in Points
- Color-coded percentage change (green = positive, red = negative)

### 3. Stock Prices Chart
- Time-series line chart
- 30-minute rolling window
- Shows price movements for all 25 stocks
- Lines with null-spanning for continuity

### 4. Top 10 Gainers
- Table showing best performing stocks
- Columns: Company Name, Symbol, Price, Change %
- Green background on percentage change

### 5. Top 10 Losers
- Table showing worst performing stocks
- Red background on percentage change

### 6. Top 10 Trading Volume
- Pie chart showing volume distribution
- Top 10 most actively traded stocks
- Shows company names and percentages

### 7. Statistics Panels
- **Active Stocks**: Count of stocks with data in last 5 minutes
- **Average Price**: Mean price across all stocks
- **Total Volume**: Sum of trading volume

## 🐳 Docker Services

### Service Details

```yaml
services:
  kafka:
    image: apache/kafka:latest
    ports: [9092:9092]
    
  kafka-ui:
    image: provectuslabs/kafka-ui
    ports: [8090:8080]
    
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    ports: [5432:5432]
    environment:
      POSTGRES_DB: egx_market
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      
  pgadmin:
    image: dpage/pgadmin4:latest
    ports: [5050:80]
    
  spark-master:
    image: apache/spark:3.4.1
    
  spark-worker:
    image: apache/spark:3.4.1
    depends_on: [spark-master]
    
  egx-producer:
    build: ./producer
    depends_on: [kafka]
    
  egx-spark-processor:
    build: ./spark-processor
    depends_on: [kafka, timescaledb, spark-master]
    
  grafana:
    image: grafana/grafana:10.0.0
    ports: [3000:3000]
```

## 🔍 Monitoring & Debugging

### View Producer Logs
```powershell
docker logs egx-producer -f
```

Expected output:
```
Connected to Kafka broker
✓ Iteration 1 [MOCK]: Published 25 stocks + 4 indices
Market is CLOSED - generating mock data
✓ Iteration 2 [MOCK]: Published 25 stocks + 4 indices
```

### View Spark Processor Logs
```powershell
docker logs egx-spark-processor -f
```

### Check Kafka Messages
1. Open Kafka UI: http://localhost:8090
2. Go to Topics → egx-stock-data
3. View messages in real-time

### Query Database Directly
```powershell
docker exec -it egx-timescaledb psql -U postgres -d egx_market
```

Useful queries:
```sql
-- Count total records
SELECT COUNT(*) FROM egx_stock_prices;

-- Latest prices for all stocks
SELECT DISTINCT ON (ticker) 
    ticker, company_name, price, price_change_percent, time
FROM egx_stock_prices 
ORDER BY ticker, time DESC;

-- Check indices only
SELECT * FROM egx_stock_prices 
WHERE ticker LIKE 'EGX%' 
ORDER BY time DESC 
LIMIT 10;
```

## 🛠️ Troubleshooting

### Producer Not Generating Data
```powershell
# Restart producer
docker-compose restart egx-producer

# Check logs
docker logs egx-producer -f
```

### Spark Job Failing
```powershell
# Check Spark logs
docker logs egx-spark-processor -f

# Restart Spark services
docker-compose restart spark-master spark-worker egx-spark-processor
```

### No Data in Grafana
1. Check TimescaleDB has data:
   ```sql
   SELECT COUNT(*) FROM egx_stock_prices;
   ```
2. Verify Grafana datasource connection (Configuration → Data sources)
3. Check query in panel (Edit panel → Query inspector)

### Kafka Issues
1. Open Kafka UI: http://localhost:8090
2. Check topic exists: `egx-stock-data`
3. Verify messages are being published
4. Check consumer groups

## 📊 Data Flow Example

```
Time: 10:30:00 (Market Open)
─────────────────────────────────────────────────────

Producer generates:
  COMI: 95.25 EGP (+2.35%)
  BTFH: 53.20 EGP (-1.88%)
  ...25 stocks
  EGX30: 27,500 Points (+1.54%)
  ...4 indices

        ↓ 30 seconds

Kafka receives 29 messages
  Partition 0: 10 messages
  Partition 1: 10 messages  
  Partition 2: 9 messages

        ↓ 10 seconds (Spark trigger)

Spark processes batch:
  - Parse JSON
  - Convert timestamps
  - Validate schema
  - Write to TimescaleDB

        ↓ 5 seconds (Grafana refresh)

Grafana queries:
  - Latest prices
  - Calculate gainers/losers
  - Aggregate statistics
  - Render dashboard

        ↓ User sees real-time update!
```

## 🎯 Use Cases

1. **Real-Time Market Monitoring**
   - Track EGX stock prices in real-time
   - Monitor market indices
   - Identify trading opportunities

2. **Historical Analysis**
   - Query historical price data
   - Analyze trading patterns
   - Generate reports

3. **Alert System**
   - Set up Grafana alerts for price thresholds
   - Get notified on significant market moves
   - Monitor specific stocks

4. **Learning & Development**
   - Practice stream processing concepts
   - Learn Kafka & Spark integration
   - Build real-time dashboards

## 🔐 Security Notes

**This is a development setup. For production:**

- Change default passwords (Postgres, Grafana, pgAdmin)
- Enable Kafka authentication (SASL/SSL)
- Use secrets management (not environment variables)
- Enable Grafana authentication
- Set up network security groups
- Use TLS/SSL for all connections

## 🚀 Performance Optimization

### For Higher Throughput
```yaml
# Increase Kafka partitions
docker exec kafka kafka-topics \
  --alter --topic egx-stock-data \
  --partitions 6 --bootstrap-server kafka:9092

# Add more Spark workers
docker-compose up -d --scale spark-worker=3
```

### For Better Query Performance
```sql
-- Add indices on TimescaleDB
CREATE INDEX idx_ticker_time ON egx_stock_prices (ticker, time DESC);
CREATE INDEX idx_time ON egx_stock_prices (time DESC);
```

## 📝 Future Enhancements

- [ ] Add real EGX API integration
- [ ] Implement alerting system
- [ ] Add more technical indicators
- [ ] Support for minute-by-minute data
- [ ] Historical data backfill
- [ ] Machine learning price prediction
- [ ] WebSocket API for live data
- [ ] Mobile app integration
- [ ] Multi-market support

## 📚 Resources

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Spark Structured Streaming](https://spark.apache.org/docs/latest/structured-streaming-programming-guide.html)
- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Egyptian Exchange Official Site](https://www.egx.com.eg/)

## 📄 License

This project is for educational purposes.

## 👤 Author

Ahmad Elsayed
- GitHub: [@ahmadelsap3](https://github.com/ahmadelsap3)

## 🙏 Acknowledgments

- Egyptian Exchange for market data inspiration
- Apache Software Foundation for Kafka & Spark
- TimescaleDB team for time-series optimization
- Grafana Labs for visualization tools
