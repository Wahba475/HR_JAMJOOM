FROM python:3.13-slim

# Unbuffered so `docker logs` shows uvicorn output immediately.
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

# Before the source, so this layer stays cached when only code changes.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
