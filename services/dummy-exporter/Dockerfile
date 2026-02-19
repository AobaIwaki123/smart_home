FROM python:3.13-slim

LABEL description="Dummy Prometheus exporter for Grafana testing"
LABEL version="1.0.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN useradd -m -u 1001 -s /bin/bash dummy-user && \
    chown -R dummy-user:dummy-user /app
USER dummy-user

EXPOSE 9100

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "9100"]
