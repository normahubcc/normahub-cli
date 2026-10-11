FROM python:3.12-alpine

WORKDIR /app

# Install standard dependencies
COPY pyproject.toml README.md ./
COPY normahub_cli/ ./normahub_cli/

RUN pip install --no-cache-dir .

EXPOSE 8000

ENV NORMAHUB_BASE_URL="https://api.normahub.cc/v1"

# Run universal gateway daemon
CMD ["normahub", "start", "-p", "8000"]
