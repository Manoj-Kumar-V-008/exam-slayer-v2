# Stage 1: Build the frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy frontend configuration files
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source files
COPY frontend/ ./

# Inject relative API URL base for production deployment
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# Stage 2: Build the backend and combine
FROM python:3.11-slim

# Set environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    TESSERACT_CMD=tesseract \
    HOME=/home/user

WORKDIR /app

# Create a non-root user with UID 1000 (standard for Hugging Face Spaces)
RUN useradd -m -u 1000 user

# Install system libraries needed for WeasyPrint, Tesseract OCR, and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libffi-dev \
    shared-mime-info \
    build-essential \
    fontconfig \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Install python packages
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application files
COPY backend/ ./

# Copy compiled frontend build from Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Pre-create directory paths
RUN mkdir -p uploads assets outputs app/templates

# Ensure the non-root user owns the /app directory
RUN chown -R user:user /app

# Switch to the non-root user
USER user

# Expose port required by Hugging Face Spaces
EXPOSE 7860

# Run FastAPI backend using Uvicorn on port 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

