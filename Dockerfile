# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Copy the files
COPY . .

RUN uv pip install --system -e .

# Run the application (PORT is set by Google Cloud Run)
CMD uvicorn slope_finder_be.api.main:app --host 0.0.0.0 --port ${PORT}