#!/bin/sh
set -e

echo "Generating nginx configuration from template..."

# Set default values if not provided
: ${WEBMAIL_HOSTNAME:=mail.${MAIL_DOMAIN}}
: ${ADMIN_HOSTNAME:=admin.${MAIL_DOMAIN}}

echo "Webmail hostname: $WEBMAIL_HOSTNAME"
echo "Admin hostname: $ADMIN_HOSTNAME"

# Substitute environment variables in template
envsubst '${WEBMAIL_HOSTNAME} ${ADMIN_HOSTNAME}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo "Nginx configuration generated. Starting nginx..."

# Execute the command passed to the container (nginx)
exec "$@"
