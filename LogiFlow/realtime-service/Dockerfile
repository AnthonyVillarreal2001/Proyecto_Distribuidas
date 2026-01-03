FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./realtime-service /app
COPY ./shared /app/shared
ENV PYTHONPATH=/app
EXPOSE 5005
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5005"]
