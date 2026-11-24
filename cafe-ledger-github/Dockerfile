FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 CAFE_DATA_DIR=/data PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 cafe \
    && mkdir /data && chown cafe:cafe /data
COPY --chown=cafe:cafe cafe ./cafe
COPY --chown=cafe:cafe templates ./templates
COPY --chown=cafe:cafe static ./static
COPY --chown=cafe:cafe serve.py backup_database.py .
USER cafe
EXPOSE 8080
CMD ["python", "serve.py"]
