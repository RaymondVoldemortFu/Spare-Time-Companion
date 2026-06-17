FROM python:3.12-slim AS backend

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY backend ./backend
COPY frontend/dist ./frontend/dist
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]

