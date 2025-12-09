# 🌊 Streaming Pipeline Setup

This pipeline streams data from EGX API -> Kafka -> Spark -> InfluxDB -> Grafana.

## 1. Start the Pipeline
Run the streaming startup script:
```bash
./scripts/start_streaming.sh
```
This will:
1. Start Kafka, Zookeeper, Spark Master/Worker, InfluxDB, and Grafana.
2. Submit the Spark Streaming job (`streaming/spark_processor.py`).
3. Start the Python Producer to fetch live data.

## 2. Configure Grafana (Local)
1. Open Grafana at [http://localhost:3000](http://localhost:3000) (User: `admin`, Pass: `admin`).
2. Go to **Connections** -> **Data Sources** -> **Add data source**.
3. Select **InfluxDB**.
4. Configure:
   - **Query Language**: `Flux`
   - **URL**: `http://influxdb:8086`
   - **Organization**: `egx`
   - **Token**: `egx-market-data-token-2025`
   - **Default Bucket**: `market_data`
5. Click **Save & Test**.

## 3. Visualize Data
Create a new dashboard and use this Flux query to see the Close Price:

```flux
from(bucket: "market_data")
  |> range(start: -1h)
  |> filter(fn: (r) => r["_measurement"] == "stock_price")
  |> filter(fn: (r) => r["_field"] == "close")
  |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
  |> yield(name: "mean")
```
