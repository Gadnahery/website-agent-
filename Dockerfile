FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV MPRINTER_OPEN_BROWSER=0
ENV MPRINTER_DATA_DIR=/var/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends golang git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/data/.mp /var/data/proposals /var/data/build-packages

CMD ["sh", "-c", "gunicorn --chdir src dashboard:app --workers 1 --threads 8 --timeout 600 --bind 0.0.0.0:${PORT:-5055}"]
