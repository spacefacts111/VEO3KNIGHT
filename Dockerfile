FROM python:3.10
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y ffmpeg fonts-dejavu

# Install Python packages step by step
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Force-install google-genai from the working wheel (bypasses PyPI issues)
RUN pip install --no-cache-dir https://github.com/google/generative-ai-python/releases/download/v0.1.0/google_genai-0.1.0-py3-none-any.whl

# Copy the rest of the app
COPY . .

CMD ["python", "main.py"]
