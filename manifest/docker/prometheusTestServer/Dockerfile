# Python 移植版 test-server(对应 Go 版 Dockerfile;与 Go 版一致,实际以原生进程方式运行)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 2112
CMD ["python", "main.py"]
