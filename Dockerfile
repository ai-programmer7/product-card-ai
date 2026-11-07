FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.18 /uv /uvx /bin/

WORKDIR /app

ENV UV_NO_DEV=1 \
    UV_NO_CACHE=1 \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./

# Устанавливаем зависимости без dev-инструментов.
RUN uv sync --frozen --no-dev --no-install-project

# Копируем исходный код.
COPY src/ ./src/

# Устанавливаем само приложение в окружение.
RUN uv sync --frozen --no-dev --no-editable

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]