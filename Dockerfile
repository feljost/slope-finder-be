# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Set working directory
WORKDIR /app

# Copy the files
COPY . .

RUN uv pip install --system -e .

# Copy the rest of your application code


# Run the application
# Cloud Run injects the PORT environment variable
CMD uvicorn slope_check_backend.api.main:app --host 0.0.0.0 --port ${PORT}