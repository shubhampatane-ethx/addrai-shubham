# Application Stack: FastAPI + React + Celery + Nginx
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    make \
    supervisor \
    nginx \
    nodejs \
    npm \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 18 (for React)
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Set working directory
WORKDIR /app

# Copy backend requirements
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy backend code
COPY backend /app/backend

# Copy frontend code
COPY frontend /app/frontend

# Install frontend dependencies and build
WORKDIR /app/frontend
RUN npm install --legacy-peer-deps
RUN npm run build

# Copy Nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy supervisor configuration
COPY scripts/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Create necessary directories
RUN mkdir -p /app/uploads /app/exports /var/log/celery /var/log/supervisor

# Set working directory back to /app
WORKDIR /app

# Expose ports
EXPOSE 80 8000

# Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
#     CMD curl -f http://localhost:8000/api/v1/health || exit 1

# # Start supervisor
# CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]


HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD sh -c "\
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 & \
    nginx -g 'daemon off;' \
"