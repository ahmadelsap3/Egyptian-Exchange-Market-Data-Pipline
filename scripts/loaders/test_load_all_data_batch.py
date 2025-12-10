"""
Bronze Layer Ingestion Script (Variant/JSON Mode) - TEST VERSION
Loads raw CSV data from S3 into Snowflake VARIANT columns.

Target Database: EGYPTIAN_STOCKS_TEST
"""

import boto3
import pandas as pd
import snowflake.connector
import io
from datetime import datetime
import os
import pytz
import json
from dotenv import load_dotenv

# Load env variables
env_path = os.path.join(os.path.dirname(__file__), '../../infrastructure/docker/.env')
load_dotenv(env_path)

# AWS S3 Configuration
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
BUCKET_NAME = 'egx-data-bucket'

# Snowflake Configuration - OVERRIDDEN FOR TEST
SNOWFLAKE_CONFIG = {
    'account': os.getenv('SNOWFLAKE_ACCOUNT', 'LPDTDON-IU51056'),
    'user': os.getenv('SNOWFLAKE_USER', 'AHMEDEHAB'),
    'password': os.getenv('SNOWFLAKE_PASSWORD'),
    'warehouse': 'COMPUTE_WH',
    'database': 'EGYPTIAN_STOCKS_TEST', # <--- OVERRIDE
    'schema': os.getenv('BRONZE_SCHEMA_NAME', 'BRONZE')
}

def get_utc_now():
    """Get stable current UTC timestamp"""
    return datetime.now(pytz.utc)

def gather_real_symbols(s3_client):
    """Scan S3 to find active symbols (used for filtering companies)"""
    print("\n🔍 Scanning S3 for active symbols...")
    real_symbols = set()
    paginator = s3_client.get_paginator('list_objects_v2')
    
    # 1. Scan TVH
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix='batch/TVH/'):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.csv'):
                sym = obj['Key'].split('/')[-1].replace('.csv', '').strip().upper()
                real_symbols.add(sym)
                
    # 2. Scan Finances
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix='batch/finances/'):
        for obj in page.get('Contents', []):
            if obj['Key'].endswith('.csv'):
                sym = obj['Key'].split('/')[-1].replace('_finance.csv', '').strip().upper()
                real_symbols.add(sym)

    print(f"✓ Found {len(real_symbols)} unique symbols")
    return real_symbols

def get_loaded_files(cursor, table_name):
    """Get set of file names already loaded in the table"""
    try:
        cursor.execute(f"SELECT DISTINCT FILE_NAME FROM {table_name}")
        return {row[0] for row in cursor.fetchall()}
    except Exception as e:
        # Table might not exist or other error
        return set()

def create_test_tables_if_not_exist(conn):
    """Ensure test tables exist before loading"""
    cursor = conn.cursor()
    try:
        print("\n🛠️ Ensuring Test Tables Exist...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {SNOWFLAKE_CONFIG['database']}")
        cursor.execute(f"USE DATABASE {SNOWFLAKE_CONFIG['database']}")
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {SNOWFLAKE_CONFIG['schema']}")
        cursor.execute(f"USE SCHEMA {SNOWFLAKE_CONFIG['schema']}")

        tables = {
            "COMPANIES_RAW": "(FILE_NAME VARCHAR, LOAD_TS TIMESTAMP_NTZ, RAW VARIANT)",
            "PRICES_RAW": "(FILE_NAME VARCHAR, LOAD_TS TIMESTAMP_NTZ, RAW VARIANT)",
            "FINANCE_RAW": "(FILE_NAME VARCHAR, LOAD_TS TIMESTAMP_NTZ, RAW VARIANT)"
        }
        
        for table, schema in tables.items():
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} {schema}")
            print(f"  ✓ {table} ready")
            
    except Exception as e:
        print(f"❌ Setup Error: {e}")
    finally:
        cursor.close()



def load_companies_raw(s3_client, conn, batch_ts):
    """Load companies to COMPANIES_RAW (VARIANT) - Incremental"""
    print("\n📊 Loading COMPANIES_RAW...")
    
    cursor = conn.cursor()
    cursor.execute(f"USE SCHEMA {SNOWFLAKE_CONFIG['schema']}")
    
    # Check for Force Refresh
    if os.getenv('FORCE_FULL_REFRESH') == '1':
        print("⚠️ FORCE_FULL_REFRESH=1: Truncating COMPANIES_RAW...")
        try: cursor.execute("TRUNCATE TABLE COMPANIES_RAW")
        except: pass
        
    loaded_files = get_loaded_files(cursor, 'COMPANIES_RAW')
    source_file = 'batch/companies/company_meta.csv'
    
    if source_file in loaded_files:
        print(f"  ⏭️ Skipping {source_file} (Already loaded)")
        return
        
    real_symbols = gather_real_symbols(s3_client)
    
    # Load & Filter
    try:
        obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=source_file)
        df = pd.read_csv(io.BytesIO(obj['Body'].read()))
        
        # Ensure 'symbol' column exists (simple check)
        if 'symbol' not in df.columns:
             # Try case insensitive lookup
             cols = {c.lower(): c for c in df.columns}
             if 'symbol' in cols:
                 df['symbol'] = df[cols['symbol']]
        
        # Filter
        df['symbol_norm'] = df['symbol'].astype(str).str.strip().str.upper()
        df = df[df['symbol_norm'].isin(real_symbols)]
        df = df.drop(columns=['symbol_norm'])
        
        # Convert to JSON rows
        values = []
        for _, row in df.iterrows():
            row_dict = row.where(pd.notnull(row), None).to_dict()
            json_str = json.dumps(row_dict)
            
            values.append((
                source_file,
                batch_ts,
                json_str
            ))

        if values:
            cursor.executemany("""
                INSERT INTO COMPANIES_RAW (FILE_NAME, LOAD_TS, RAW)
                SELECT Column1, Column2, PARSE_JSON(Column3)
                FROM VALUES (%s, %s, %s)
            """, values)
            
        print(f"✓ Inserted {len(values)} rows into COMPANIES_RAW")
        
    except Exception as e:
        print(f"❌ Error loading {source_file}: {e}")
        
    cursor.close()

def load_prices_raw(s3_client, conn, batch_ts):
    """Load TVH prices to PRICES_RAW (VARIANT) - Incremental"""
    print("\n📈 Loading PRICES_RAW...")
    cursor = conn.cursor()
    cursor.execute(f"USE SCHEMA {SNOWFLAKE_CONFIG['schema']}")
    
    if os.getenv('FORCE_FULL_REFRESH') == '1':
        print("⚠️ FORCE_FULL_REFRESH=1: Truncating PRICES_RAW...")
        try: cursor.execute("TRUNCATE TABLE PRICES_RAW")
        except: pass

    # Get already loaded files
    loaded_files = get_loaded_files(cursor, 'PRICES_RAW')
    print(f"  ℹ️ Found {len(loaded_files)} files already loaded in PRICES_RAW")

    all_rows = []
    paginator = s3_client.get_paginator('list_objects_v2')
    processed = 0
    skipped = 0
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix='batch/TVH/'):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if not key.endswith('.csv'): continue
            
            if key in loaded_files:
                skipped += 1
                continue
            
            try:
                s3_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
                df = pd.read_csv(io.BytesIO(s3_obj['Body'].read()), dtype=str)
                symbol = key.split('/')[-1].replace('.csv', '').strip().upper()
                
                for _, row in df.iterrows():
                    row_dict = row.where(pd.notnull(row), None).to_dict()
                    row_dict['_ingest_symbol'] = symbol 
                    
                    all_rows.append((
                        key,
                        batch_ts,
                        json.dumps(row_dict)
                    ))
                
                processed += 1
                if processed % 50 == 0:
                    print(f"  Processed {processed} new files... (Skipped {skipped} so far)")
                    
            except Exception as e:
                print(f"Error {key}: {e}")

    # Batch Insert
    if all_rows:
        print(f"  Inserting {len(all_rows)} records...")
        for i in range(0, len(all_rows), 5000):
            batch = all_rows[i:i+5000]
            cursor.executemany("""
                INSERT INTO PRICES_RAW (FILE_NAME, LOAD_TS, RAW)
                SELECT Column1, Column2, PARSE_JSON(Column3)
                FROM VALUES (%s, %s, %s)
            """, batch)
            
    print(f"✓ Loaded PRICES_RAW (Processed {processed}, Skipped {skipped})")
    cursor.close()

def load_financials_raw(s3_client, conn, batch_ts):
    """Load financials to FINANCE_RAW (VARIANT) - Incremental"""
    print("\n💰 Loading FINANCE_RAW...")
    cursor = conn.cursor()
    cursor.execute(f"USE SCHEMA {SNOWFLAKE_CONFIG['schema']}")
    
    if os.getenv('FORCE_FULL_REFRESH') == '1':
        print("⚠️ FORCE_FULL_REFRESH=1: Truncating FINANCE_RAW...")
        try: cursor.execute("TRUNCATE TABLE FINANCE_RAW")
        except: pass

    loaded_files = get_loaded_files(cursor, 'FINANCE_RAW')
    print(f"  ℹ️ Found {len(loaded_files)} files already loaded in FINANCE_RAW")

    all_rows = []
    paginator = s3_client.get_paginator('list_objects_v2')
    skipped = 0
    processed = 0
    skipped_empty = 0
    
    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix='batch/finances/'):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if not key.endswith('.csv'): continue
            
            if key in loaded_files:
                skipped += 1
                continue
            
            try:
                s3_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
                df = pd.read_csv(io.BytesIO(s3_obj['Body'].read()), dtype=str)
                
                if df.empty: # Check if DataFrame is empty
                    skipped_empty += 1
                    continue # Skip to the next file
                
                symbol = key.split('/')[-1].replace('_finance.csv', '').strip().upper()
                
                for _, row in df.iterrows():
                    row_dict = row.where(pd.notnull(row), None).to_dict()
                    row_dict['_ingest_symbol'] = symbol
                    
                    all_rows.append((
                        key,
                        batch_ts,
                        json.dumps(row_dict)
                    ))
                processed += 1
            except Exception as e:
                print(f"Error {key}: {e}")
                
    if all_rows:
        for i in range(0, len(all_rows), 5000):
            batch = all_rows[i:i+5000]
            cursor.executemany("""
                INSERT INTO FINANCE_RAW (FILE_NAME, LOAD_TS, RAW)
                SELECT Column1, Column2, PARSE_JSON(Column3)
                FROM VALUES (%s, %s, %s)
            """, batch)
            
    print(f"✓ Loaded FINANCE_RAW (Processed {processed}, Skipped {skipped}, Empty {skipped_empty})")
    cursor.close()

def main():
    print("🚀 BRONZE RAW (JSON) LOADER - TEST VER")
    print(f"Target DB: {SNOWFLAKE_CONFIG['database']}")
    
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY
    )
    
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    batch_ts = get_utc_now()
    

    try:
        create_test_tables_if_not_exist(conn)
        load_companies_raw(s3_client, conn, batch_ts)
        load_prices_raw(s3_client, conn, batch_ts)
        load_financials_raw(s3_client, conn, batch_ts)
        
        print("\n✅ Load Complete")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
