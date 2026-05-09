# FROM python:3.13-slim

# RUN apt-get update && apt-get install -y \
#     libpango-1.0-0 \
#     libcairo2 \
#     libpangoft2-1.0-0 \
#     libgdk-pixbuf-xlib-2.0-0 \
#     libffi-dev \
#     shared-mime-info \
#     && rm -rf /var/lib/apt/lists/*

# WORKDIR /app

# COPY requirements.txt .
# RUN pip install -r requirements.txt

# COPY . .

# CMD gunicorn cv_builder.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 1

FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libdrm2 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium

COPY . .

CMD gunicorn cv_builder.wsgi --bind 0.0.0.0:${PORT:-8000} --workers 1