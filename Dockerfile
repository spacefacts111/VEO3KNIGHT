FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y ffmpeg wget libnss3 libatk-bridge2.0-0 libatk1.0-0 libgtk-3-0 libasound2 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir playwright && playwright install chromium
COPY . .
EXPOSE 8080
CMD ["python", "main.py"]
