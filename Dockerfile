FROM python:3.15.1

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev
ENV PATH="/app/.venv/bin:$PATH"

COPY . .

CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]