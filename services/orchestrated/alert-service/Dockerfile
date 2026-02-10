FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY shared/ /app/shared/
COPY services/orchestrated/alert-service/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY services/orchestrated/alert-service/app/ /app/app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10003"]
