FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py /app/

EXPOSE 8089 9646

# Default command (can be overridden)
CMD ["locust", "--host=http://localhost:14000"]
