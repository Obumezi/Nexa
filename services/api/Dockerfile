FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PYTHONPATH=/app/src

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY .agents ./.agents

# Alembic migration files required for production PostgreSQL
COPY alembic.ini ./
COPY migrations ./migrations

RUN pip install --upgrade pip \
    && pip install -e .

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn nexa_api.main:app --host 0.0.0.0 --port 8000"]