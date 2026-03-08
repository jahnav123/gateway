FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8080

# Run the application
CMD python3 init_db_postgres.py && python3 -m uvicorn server:app --host 0.0.0.0 --port 8080
