FROM python:3.10
WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y ffmpeg fonts-dejavu

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Install Playwright Chromium
RUN playwright install --with-deps chromium

COPY . .

CMD ["python", "main.py"]
