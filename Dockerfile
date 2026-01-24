FROM python:3.12-alpine

ENV IS_DOCKER true

WORKDIR /app

RUN apk update && \
    apk upgrade --no-cache && \
    apk add --no-cache chromium chromium-chromedriver && \
    rm -rf /var/cache/apk/*

COPY . .

RUN pip3 install --no-cache-dir -e .

ENTRYPOINT ["python", "noip-renew.py"]
