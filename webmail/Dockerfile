FROM python:3.11-slim

WORKDIR /app

# Install supervisor
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY webmail/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY webmail/ .

# Copy postfix services (for imports)
COPY postfix/*.py .

# Create necessary directories
RUN mkdir -p /app/attachments /var/log/supervisor

# Copy supervisor config
COPY webmail/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 5001

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
