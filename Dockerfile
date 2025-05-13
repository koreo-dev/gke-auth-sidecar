FROM gcr.io/google.com/cloudsdktool/cloud-sdk:slim

# Optional: Install Python dependencies (already includes Python 3.x)
RUN apt-get update && apt-get install -y python3-pip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY sidecar.py /app/sidecar.py
WORKDIR /app

ENTRYPOINT ["python3", "sidecar.py"]
