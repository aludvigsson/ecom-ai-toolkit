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

# /healthz returns 503 until SHOPIFY_WEBHOOK_SECRET is set, so a misconfigured
# container is marked unhealthy instead of silently 500-ing every webhook.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/healthz').status==200 else 1)"

CMD ["uv", "run", "uvicorn", "shopify.scripts.webhooks.receiver.app:app", "--host", "0.0.0.0", "--port", "8000"]
