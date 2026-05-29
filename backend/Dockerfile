FROM python:3.11-slim

WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app
COPY data /data
ENV DEMO_FIXTURE_DIR=/data/fixtures/beirut
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
