FROM python:3.12-slim

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra shopify --extra webhooks --no-dev

COPY core ./core
COPY shopify ./shopify

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "shopify.scripts.webhooks.receiver.app:app", "--host", "0.0.0.0", "--port", "8000"]
