import time
import json
import random
import os
import logging
from datetime import datetime
from kafka import KafkaProducer
import yfinance as yf

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
TOPIC_NAME = 'egx_market_data'
USE_MOCK_DATA = os.environ.get('USE_MOCK_DATA', 'false').lower() == 'true'
TICKER_INTERVAL_SEC = int(os.environ.get('TICKER_INTERVAL_SEC', 10))

# EGX 30 Top Stocks (Approximate list)
EGX_TICKERS = [
    "COMI.CA", # CIB
    "HRHO.CA", # EFG Hermes
    "EMFD.CA", # Emaar Misr
    "ETEL.CA", # Telecom Egypt
    "SWDY.CA", # Elsewedy Electric
    "AUTO.CA", # GB Auto
    "FWRY.CA", # Fawry
    "EAST.CA", # Eastern Company
    "TMGH.CA", # TMG Holding
    "ORAS.CA", # Orascom Construction
]

def create_producer():
    producer = None
    while not producer:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            logger.info("Connected to Kafka!")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}. Retrying in 5 seconds...")
            time.sleep(5)
    return producer

def fetch_yfinance_data(tickers):
    """
    Fetches real-time(ish) data from Yahoo Finance.
    Returns a list of dicts.
    """
    data = []
    try:
        # Fetch data for all tickers at once
        tickers_str = " ".join(tickers)
        # downloading last 1 day with 1 minute interval to get the latest 'row'
        df = yf.download(tickers_str, period="1d", interval="1m", group_by='ticker', threads=True, progress=False)
        
        timestamp = datetime.now().isoformat()
        
        for ticker in tickers:
            try:
                # Handle multi-index columns from yfinance
                ticker_df = df[ticker]
                if not ticker_df.empty:
                    last_quote = ticker_df.iloc[-1]
                    # Check if NaN (happens if market is closed/no data)
                    price = last_quote['Close']
                    volume = last_quote['Volume']
                    
                    if hasattr(price, 'item'): price = price.item() # convert numpy types
                    if hasattr(volume, 'item'): volume = volume.item()
                    
                    # If NaN, might be pre-market or connection issue. 
                    # For demo purposes, we might want to skip or fill.
                    if (price != price): # NaN check
                         continue

                    record = {
                        "ticker": ticker,
                        "price": float(price),
                        "volume": int(volume),
                        "timestamp": timestamp,
                        "source": "yfinance"
                    }
                    data.append(record)
            except Exception as e:
                logger.warning(f"Error processing ticker {ticker}: {e}")
                
    except Exception as e:
        logger.error(f"Error fetching data from yfinance: {e}")
    
    return data

def generate_mock_data(tickers):
    """
    Generates random mock data for testing when API is unavailable or market is closed.
    """
    data = []
    timestamp = datetime.now().isoformat()
    for ticker in tickers:
        price = round(random.uniform(10, 100), 2)
        volume = random.randint(1000, 50000)
        record = {
            "ticker": ticker,
            "price": price,
            "volume": volume,
            "timestamp": timestamp,
            "source": "mock"
        }
        data.append(record)
    return data

def main():
    logger.info("Starting EGX Data Producer...")
    producer = create_producer()
    
    while True:
        if USE_MOCK_DATA:
            logger.info("Fetching MOCK data...")
            records = generate_mock_data(EGX_TICKERS)
        else:
            logger.info("Fetching YFINANCE data...")
            records = fetch_yfinance_data(EGX_TICKERS)
            
            # If market is closed or API fails, fallback to mock if list is empty?
            # Or just wait. Let's fallback to mock if empty to keep the dashboard alive for the student project.
            if not records:
                logger.warning("No data from yfinance (Market closed?). Falling back to MOCK data for demo.")
                records = generate_mock_data(EGX_TICKERS)

        for record in records:
            # logger.info(f"Producing: {record}")
            producer.send(TOPIC_NAME, record)
        
        producer.flush()
        logger.info(f"Pushed {len(records)} records to Kafka.")
        time.sleep(TICKER_INTERVAL_SEC)

if __name__ == "__main__":
    main()
