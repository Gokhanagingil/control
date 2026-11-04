FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
RUN useradd --system --uid 10001 --create-home control && mkdir -p /data && chown control:control /data
USER control
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CONTROL_DB=/data/control.db CONTROL_HOST=0.0.0.0 PORT=8080
EXPOSE 8080
CMD ["python","/app/app.py"]
