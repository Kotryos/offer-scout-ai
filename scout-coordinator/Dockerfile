FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN pip install --no-cache-dir --no-deps .

ENV PORT=8080

CMD ["sh", "-c", "uvicorn scout_coordinator.main:app --host 0.0.0.0 --port ${PORT}"]
