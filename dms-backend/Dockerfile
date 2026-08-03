# Optional container path — the default POC workflow is the local venv (see README.md).
# Use this when Docker Desktop is available and you want the backend running in a container.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

RUN mkdir -p storage/evidence/images storage/evidence/videos

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
