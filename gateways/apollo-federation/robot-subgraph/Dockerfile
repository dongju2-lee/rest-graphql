FROM python:3.11-slim

WORKDIR /app

COPY gateways/apollo-federation/robot-subgraph/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gateways/apollo-federation/robot-subgraph/app/ /app/app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10011"]
