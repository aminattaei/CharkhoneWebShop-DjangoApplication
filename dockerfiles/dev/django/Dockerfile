FROM python:3.11-slim-bookworm

LABEL maintainer="aminattaei2000@gmail.com"

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

COPY ./requirements.txt .

RUN pip install --upgrade pip && pip install --no-cache -r requirements.txt

COPY ./core .