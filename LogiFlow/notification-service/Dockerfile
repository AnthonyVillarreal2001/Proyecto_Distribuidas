FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy common requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code and shared module
COPY ./notification-service /app
COPY ./shared /app/shared

ENV PYTHONPATH=/app
EXPOSE 5007
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5007"]
