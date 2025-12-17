FROM python:3.11-slim

WORKDIR /app
# Copy dependencies from project root (build context is LogiFlow/)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy service code and shared module
COPY ./auth-service /app
COPY ./shared /app/shared

# Ensure shared is importable
ENV PYTHONPATH=/app
EXPOSE 5001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
