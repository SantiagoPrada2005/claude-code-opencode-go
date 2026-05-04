FROM python:3.12-slim

WORKDIR /app

RUN groupadd -r proxy && useradd -r -g proxy proxy

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY proxy-server.py .

RUN mkdir -p /app/data && chown -R proxy:proxy /app
USER proxy

EXPOSE 11434

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/health')" || exit 1

CMD ["python", "proxy-server.py"]
