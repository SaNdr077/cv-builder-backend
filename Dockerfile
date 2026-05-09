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

FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libcairo2 \
    libpangoft2-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

# 🔥 IMPORTANT: install chromium inside container
RUN python -m playwright install --with-deps chromium

COPY . .

ENV PYTHONUNBUFFERED=1

CMD gunicorn cv_builder.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1