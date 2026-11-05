FROM python:3.12-slim
WORKDIR /app
COPY app.py ui.py ui_v2.py ksgrc.js identity.py bootstrap.py backup.py seed_reference.py seed_itil.py execution_service.py grc_plus.py grc_excel.py xlsx_io.py /app/
COPY seed/ /app/seed/
RUN useradd --system --uid 10001 --create-home control && mkdir -p /data && chown control:control /data
USER control
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CONTROL_DB=/data/control.db CONTROL_HOST=0.0.0.0 PORT=8080
EXPOSE 8080
CMD ["python","/app/app.py"]
