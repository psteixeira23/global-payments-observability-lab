FROM python:3.12-slim

ENV POETRY_VERSION=1.8.4
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/workspace

RUN pip install "poetry==$POETRY_VERSION" \
    && groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home --home-dir /home/appuser appuser

WORKDIR /workspace
COPY pyproject.toml /workspace/
RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction --no-ansi

COPY --chown=appuser:appgroup shared /workspace/shared
COPY --chown=appuser:appgroup services/payments-api /workspace/services/payments-api

WORKDIR /workspace/services/payments-api
USER appuser
EXPOSE 8080
CMD ["poetry", "run", "uvicorn", "payments_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
