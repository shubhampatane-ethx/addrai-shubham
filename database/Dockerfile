# Database Stack: PostgreSQL + Redis
FROM postgres:15-alpine

# Install Redis
RUN apk add --no-cache redis supervisor

# Create directories
RUN mkdir -p /var/log/supervisor /var/run/redis

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy Redis configuration
COPY redis.conf /etc/redis/redis.conf

# Expose ports
EXPOSE 5432 6379

# Start supervisor to manage both PostgreSQL and Redis
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
