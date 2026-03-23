FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV MPRINTER_OPEN_BROWSER=0
ENV MPRINTER_DATA_DIR=/var/data

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        golang \
        git \
        ca-certificates \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxkbcommon0 \
        libxrandr2 \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /var/data/.mp /var/data/proposals /var/data/build-packages

CMD ["sh", "-c", "gunicorn --chdir src dashboard:app --workers 1 --threads 8 --timeout 600 --bind 0.0.0.0:${PORT:-5055}"]
