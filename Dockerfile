FROM python:3.11-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir --upgrade pip setuptools "wheel>=0.46.2"
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /install /usr/local

RUN pip install --no-cache-dir --upgrade "wheel>=0.46.2"

COPY . .

# 使用 gunicorn 多worker + uvicorn workers
RUN pip install --no-cache-dir gunicorn

EXPOSE 35827

CMD ["gunicorn", "--bind", "0.0.0.0:8001", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "app.main:app"]
