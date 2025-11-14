#!/bin/bash
set -e

echo "Starting Dovecot configuration..."

# Replace placeholders in SQL config
sed -i "s/%DB_USER%/$DB_USER/g" /etc/dovecot/dovecot-sql.conf.ext
sed -i "s/%DB_PASSWORD%/$DB_PASSWORD/g" /etc/dovecot/dovecot-sql.conf.ext
sed -i "s/%DB_NAME%/$DB_NAME/g" /etc/dovecot/dovecot-sql.conf.ext

# Set proper permissions
chmod 600 /etc/dovecot/dovecot-sql.conf.ext
chown -R vmail:mail /var/mail
mkdir -p /var/mail
chmod 770 /var/mail

# Create necessary directories
mkdir -p /var/run/dovecot
chown -R dovecot:dovecot /var/run/dovecot

echo "Dovecot configured. Starting services..."

# Start services using supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
