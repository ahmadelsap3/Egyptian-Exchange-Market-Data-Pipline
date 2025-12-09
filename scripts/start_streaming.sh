#!/bin/bash
# Quick start for EGX streaming pipeline - ALL COMPANIES
# Usage: ./start_streaming.sh

echo "🚀 Starting EGX Streaming Pipeline (249 companies)..."
echo "========================================="

# Get all company symbols from Snowflake
echo "📊 Fetching all company symbols from Snowflake..."
cd egx_dw
source ../.venv-aws/bin/activate
export $(cat .env | grep -v '^#' | xargs)

# Get comma-separated list of all symbols
SYMBOLS=$(python -c "
import snowflake.connector
conn = snowflake.connector.connect(
    account='LPDTDON-IU51056',
    user='$SNOWFLAKE_USER',
    password='$SNOWFLAKE_PASSWORD',
    warehouse='COMPUTE_WH'
)
cursor = conn.cursor()
cursor.execute('SELECT symbol FROM EGX_OPERATIONAL_DB.OPERATIONAL.TBL_COMPANY ORDER BY symbol')
symbols = [row[0] for row in cursor]
print(','.join(symbols))
")

echo "✓ Found $(echo $SYMBOLS | tr ',' '\n' | wc -l) companies"

# 1. Start Infrastructure (Kafka, Spark, InfluxDB, Grafana)
echo "📦 Starting Infrastructure (Kafka, Spark, InfluxDB, Grafana)..."
cd ../infrastructure/docker
docker compose up -d zookeeper kafka spark-master spark-worker influxdb grafana
sleep 15

# 2. Install Dependencies on Spark Master
echo "🔧 Installing Python dependencies on Spark Master..."
docker exec spark-master pip install influxdb-client

# 3. Submit Spark Job
echo "⚡ Submitting Spark Streaming Job..."
docker cp ../../streaming/spark_processor.py spark-master:/opt/bitnami/spark/

# Submit in background
docker exec -d spark-master spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0 \
  /opt/bitnami/spark/spark_processor.py

echo "✓ Spark Job Submitted"

# 4. Start Producer (EGX API → Kafka) with ALL companies
echo "📡 Starting EGX Producer with ALL companies..."
cd ../../
source .venv-aws/bin/activate

# Start producer in background - fetches last 10 days for all companies every 5 min
nohup python streaming/producer.py \
  --symbols "$SYMBOLS" \
  --interval Daily \
  --n-bars 10 \
  --poll-interval 300 > logs/producer.log 2>&1 &
PRODUCER_PID=$!
echo "✓ Producer running (PID: $PRODUCER_PID) - check logs/producer.log"

# 3. Start Consumer (Kafka → Snowflake)
echo "💾 Starting Snowflake Consumer..."
nohup python streaming/consumer_snowflake.py \
  --topic egx_market_data \
  --batch-size 100 \
  --batch-timeout 30 > logs/consumer.log 2>&1 &
CONSUMER_PID=$!
echo "✓ Consumer running (PID: $CONSUMER_PID) - check logs/consumer.log"

echo ""
echo "========================================="
echo "✅ Streaming pipeline started for 249 companies!"
echo ""
echo "Processes:"
echo "  Producer PID: $PRODUCER_PID"
echo "  Consumer PID: $CONSUMER_PID"
echo ""
echo "To stop:"
echo "  kill $PRODUCER_PID $CONSUMER_PID"
echo "  docker compose -f infrastructure/docker/docker-compose.yml down"
echo ""
echo "Monitor logs:"
echo "  tail -f logs/producer.log"
echo "  tail -f logs/consumer.log"
echo ""
echo "Data flows: EGX API → Kafka → Snowflake → dbt"
