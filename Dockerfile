FROM python:3.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get clean && \
    apt-get update -y && \
    apt-get install -y --no-install-recommends \
    curl \
    netcat \
    build-essential \
    bash \
    gettext \
    ffmpeg -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

RUN pip install django-environ

ENV ENV_FILE_PATH=/app/.env

COPY .deploy/bot.sh /
RUN chmod +x /bot.sh

COPY .deploy/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

ENTRYPOINT ["/bin/bash", "/bot.sh"]
