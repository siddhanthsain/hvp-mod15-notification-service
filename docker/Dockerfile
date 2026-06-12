FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir -e .

EXPOSE 8015

CMD ["uvicorn", "hvp_mod15_notification_service.main:app",
     "--host", "0.0.0.0", "--port", "8015", "--app-dir", "src"]
