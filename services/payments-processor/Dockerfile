FROM python:3.12-slim

ENV POETRY_VERSION=1.8.4
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/workspace

RUN pip install "poetry==$POETRY_VERSION"

WORKDIR /workspace
COPY pyproject.toml /workspace/
RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction --no-ansi

COPY shared /workspace/shared
COPY services/payments-processor /workspace/services/payments-processor

WORKDIR /workspace/services/payments-processor
CMD ["poetry", "run", "python", "-m", "payments_processor.main"]
