FROM apache/spark:3.4.1

USER root

# Install Python dependencies
RUN pip install --no-cache-dir \
    psycopg2-binary==2.9.9

# Copy application
COPY egx_spark_job.py /app/
WORKDIR /app

CMD ["/opt/spark/bin/spark-submit", \
     "--packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,org.postgresql:postgresql:42.7.0", \
     "--master", "spark://spark-master:7077", \
     "egx_spark_job.py"]
