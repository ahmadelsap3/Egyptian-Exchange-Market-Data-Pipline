"""
EGX Stock Data Processor using Apache Spark Structured Streaming
Consumes from Kafka and writes to TimescaleDB
"""
import os
import logging
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, current_timestamp, to_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, BooleanType
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'egx-stock-data')
TIMESCALE_HOST = os.getenv('TIMESCALE_HOST', 'timescaledb')
TIMESCALE_PORT = os.getenv('TIMESCALE_PORT', '5432')
TIMESCALE_DB = os.getenv('TIMESCALE_DB', 'egx_market')
TIMESCALE_USER = os.getenv('TIMESCALE_USER', 'postgres')
TIMESCALE_PASSWORD = os.getenv('TIMESCALE_PASSWORD', 'postgres')

# Define schema for incoming JSON data
schema = StructType([
    StructField("ticker", StringType(), True),
    StructField("company_name", StringType(), True),
    StructField("price", DoubleType(), True),
    StructField("open", DoubleType(), True),
    StructField("high", DoubleType(), True),
    StructField("low", DoubleType(), True),
    StructField("volume", LongType(), True),
    StructField("price_change", DoubleType(), True),
    StructField("price_change_percent", DoubleType(), True),
    StructField("currency", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("source", StringType(), True),
    StructField("exchange", StringType(), True),
    StructField("is_mock", BooleanType(), True),
    StructField("market_status", StringType(), True)
])


def ensure_table_exists():
    """Create TimescaleDB table if not exists"""
    try:
        conn = psycopg2.connect(
            host=TIMESCALE_HOST,
            port=TIMESCALE_PORT,
            database=TIMESCALE_DB,
            user=TIMESCALE_USER,
            password=TIMESCALE_PASSWORD
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS egx_stock_prices (
                time TIMESTAMPTZ NOT NULL,
                ticker TEXT NOT NULL,
                company_name TEXT,
                price DOUBLE PRECISION,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                volume BIGINT,
                price_change DOUBLE PRECISION,
                price_change_percent DOUBLE PRECISION,
                currency TEXT,
                source TEXT,
                exchange TEXT,
                is_mock BOOLEAN,
                market_status TEXT
            );
        """)
        
        try:
            cursor.execute("""
                SELECT create_hypertable('egx_stock_prices', 'time', 
                    if_not_exists => TRUE,
                    chunk_time_interval => INTERVAL '1 day'
                );
            """)
            logger.info("✓ Hypertable created")
        except Exception as e:
            if "already a hypertable" not in str(e):
                logger.warning(f"Hypertable note: {e}")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker_time ON egx_stock_prices (ticker, time DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_status ON egx_stock_prices (market_status, time DESC);")
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✓ Table ensured")
    except Exception as e:
        logger.error(f"Error ensuring table: {e}")


def write_to_timescale(batch_df, batch_id):
    """Write batch to TimescaleDB"""
    if batch_df.isEmpty():
        return
    
    try:
        jdbc_url = f"jdbc:postgresql://{TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}"
        
        batch_df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", "egx_stock_prices") \
            .option("user", TIMESCALE_USER) \
            .option("password", TIMESCALE_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .mode("append") \
            .save()
        
        count = batch_df.count()
        logger.info(f"✓ Batch {batch_id}: Wrote {count} records to TimescaleDB")
    except Exception as e:
        logger.error(f"Error writing batch {batch_id}: {e}")


def main():
    logger.info("🚀 Starting EGX Spark Streaming Processor")
    
    # Ensure table exists
    ensure_table_exists()
    
    # Create Spark session
    spark = SparkSession.builder \
        .appName("EGX-Stock-Processor") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,org.postgresql:postgresql:42.7.0") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    logger.info(f"✓ Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"✓ Topic: {KAFKA_TOPIC}")
    logger.info(f"✓ TimescaleDB: {TIMESCALE_HOST}:{TIMESCALE_PORT}/{TIMESCALE_DB}")
    
    # Read from Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", KAFKA_TOPIC) \
        .option("startingOffsets", "earliest") \
        .load()
    
    # Parse JSON
    parsed_df = df.select(
        from_json(col("value").cast("string"), schema).alias("data")
    ).select("data.*")
    
    # Rename timestamp to time and convert to proper timestamp type
    final_df = parsed_df \
        .withColumnRenamed("timestamp", "time") \
        .withColumn("time", to_timestamp(col("time")))
    
    # Write to TimescaleDB
    query = final_df.writeStream \
        .foreachBatch(write_to_timescale) \
        .outputMode("append") \
        .option("checkpointLocation", "/tmp/spark-checkpoint") \
        .start()
    
    logger.info("✓ Streaming started - Processing EGX stock data...")
    query.awaitTermination()


if __name__ == "__main__":
    main()
