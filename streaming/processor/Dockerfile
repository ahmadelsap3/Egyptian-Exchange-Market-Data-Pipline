FROM eclipse-temurin:11-jre

# Install Python
RUN apt-get update && \
    apt-get install -y python3 python3-pip procps && \
    ln -s /usr/bin/python3 /usr/bin/python && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy job
COPY spark_job.py .

# Submit spark job locally
CMD ["python", "spark_job.py"]
