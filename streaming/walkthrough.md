# EGX Real-time Streaming Pipeline - Walkthrough

## Overview
This project implements a real-time data pipeline for the Egyptian Stock Market (EGX).
It uses a microservices architecture to ingest, process, and visualize market data.

## Architecture
```mermaid
graph LR
    A[Producer (Python/yfinance)] -->|JSON| B[Kafka (Topic: egx_market_data)]
    B -->|Stream| C[Processor (PySpark)]
    C -->|Write| D[InfluxDB]
    D -->|Query| E[Grafana Dashboard]
```

### Components
1.  **Producer**: Fetches data from standard financial APIs (Yahoo Finance) or generates mock data if markets are closed. Simulates real-time ticks.
2.  **Kafka & Zookeeper**: Handles message queuing and decoupling.
3.  **Processor**: standalone PySpark container that reads from Kafka, performs transformations (e.g., data cleaning, aggregation), and writes to InfluxDB.
4.  **InfluxDB**: Time-series database for high-speed write/read.
5.  **Grafana**: Visualization dashboard pre-configured to show Real-time Prices and Trading Volume.

## How to Run
The entire system is Dockerized.

### 1. Start the Pipeline
```bash
cd egx_pipeline
docker compose up -d --build
```
*Note: The first run might take a few minutes to pull Docker images.*

### 2. Verify Services
Check if all containers are running:
```bash
docker compose ps
```

Check the Producer logs to see data being fetched:
```bash
docker compose logs -f producer
```

Check the Processor logs to see Spark processing batches:
```bash
docker compose logs -f processor
```

### 3. View Dashboard
1.  Open your browser to [http://localhost:3000](http://localhost:3000).
2.  Login with:
    *   **User**: `admin`
    *   **Password**: `admin`
3.  Navigate to **Dashboards** > **Browse** > **EGX Market Overview**.

## Features Implemented
*   **Resiliency**: Producer auto-retries Kafka connection.
*   **Fallback**: Automatically switches to Mock Data if API returns empty (e.g., weekends/market closed), ensuring the demo always works.
*   **Scalability**: Architecture supports scaling Spark workers (though configured for standalone here for simplicity).
*   **IaC**: Grafana dashboards and datasources are provisioned as code (no manual setup required).
