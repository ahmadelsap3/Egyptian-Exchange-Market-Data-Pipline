import os
import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType, IntegerType
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SparkHandler")

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
TOPIC_NAME = 'egx_market_data'

INFLUXDB_URL = os.environ.get('INFLUXDB_URL', 'http://influxdb:8086')
INFLUXDB_TOKEN = os.environ.get('INFLUXDB_TOKEN', 'my-super-secret-auth-token')
INFLUXDB_ORG = os.environ.get('INFLUXDB_ORG', 'my-org')
INFLUXDB_BUCKET = os.environ.get('INFLUXDB_BUCKET', 'egx_market_data')

def write_to_influx(batch_df, batch_id):
    """
    ForeachBatch function to write data to InfluxDB.
    """
    data = batch_df.collect()
    if not data:
        return

    client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)
    
    points = []
    for row in data:
        # Schema: ticker, price, volume, timestamp(source), sma_1min
        try:
            p = Point("stock_price") \
                .tag("ticker", row['ticker']) \
                .field("price", float(row['price'])) \
                .field("volume", int(row['volume'])) \
                .field("sma_1min", float(row.get('sma_1min', 0.0))) \
                .time(row['timestamp'])
            points.append(p)
        except Exception as e:
            logger.error(f"Error creating point: {e}")

    try:
        if points:
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)
            logger.info(f"Batch {batch_id}: Wrote {len(points)} records to InfluxDB.")
    except Exception as e:
        logger.error(f"Error writing to InfluxDB: {e}")
    finally:
        client.close()

def main():
    spark = SparkSession.builder \
        .appName("EGXRealTimeProcessor") \
        .master("local[*]") \
        .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    # Define Schema
    schema = StructType([
        StructField("ticker", StringType()),
        StructField("price", DoubleType()),
        StructField("volume", IntegerType()),
        StructField("timestamp", StringType()), # Timestamp comes as string from source
        StructField("source", StringType())
    ])

    # Read from Kafka
    df = spark \
        .readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS) \
        .option("subscribe", TOPIC_NAME) \
        .option("startingOffsets", "latest") \
        .load()

    # Parse JSON
    parsed_df = df.select(from_json(col("value").cast("string"), schema).alias("data")).select("data.*")
    
    # Convert timestamp string to TimestampType for windowing
    # Incoming format is ISO e.g., 2023-10-27T10:00:00.000000
    parsed_df = parsed_df.withColumn("timestamp", col("timestamp").cast(TimestampType()))

    # Basic Transformation: Filter out 0 prices.
    clean_df = parsed_df.filter(col("price") > 0)

    query = clean_df.writeStream \
        .foreachBatch(write_to_influx) \
        .start()

    query.awaitTermination()

if __name__ == "__main__":
    main()
