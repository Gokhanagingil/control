FROM python:3.12-alpine@sha256:213242b537a1c166a0c53e903461fc18d5518e7196c93dbecda452660a848918
WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --disable-pip-version-check --no-cache-dir --only-binary=:all: --require-hashes -r requirements.txt \
    && python -m pip uninstall -y pip \
    && rm -rf /usr/local/lib/python3.12/ensurepip \
    && addgroup -S -g 10001 control && adduser -S -D -u 10001 -G control control \
    && mkdir -p /data && chown control:control /data && chmod 0700 /data
COPY *.py ksgrc.js architecture.svg /app/
COPY seed/ /app/seed/
USER 10001:10001
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CONTROL_DB=/data/control.db CONTROL_HOST=0.0.0.0 PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD ["python", "-c", "import http.client; c=http.client.HTTPConnection('127.0.0.1',8080,timeout=3); c.request('GET','/api/health'); r=c.getresponse(); raise SystemExit(r.status!=401)"]
CMD ["python","/app/app.py"]
