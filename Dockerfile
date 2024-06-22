FROM python:3.12-alpine

WORKDIR /app

COPY requirements.txt .

RUN apk update && \
    apk upgrade --no-cache && \
    apk add --no-cache chromium chromium-chromedriver && \
    rm -rf /var/cache/apk/* && \
    pip3 install --no-cache-dir -r requirements.txt

COPY noip-renew.py constants.py .

ENTRYPOINT ["python3", "noip-renew.py"]
