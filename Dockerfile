FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY web ./web
RUN pip install --no-cache-dir -e .
ENV PORT=8765 HOST=0.0.0.0 PYTHONUNBUFFERED=1
EXPOSE 8765
CMD ["python", "-m", "kimarite.b10_web"]
