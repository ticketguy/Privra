#!/bin/bash
set -e

echo "Starting Postfix configuration..."

# Replace placeholders in PostgreSQL config files
sed -i "s/%DB_USER%/$DB_USER/g" /etc/postfix/pgsql-*.cf
sed -i "s/%DB_PASSWORD%/$DB_PASSWORD/g" /etc/postfix/pgsql-*.cf
sed -i "s/%DB_NAME%/$DB_NAME/g" /etc/postfix/pgsql-*.cf

# Replace placeholders in main.cf
sed -i "s/\$MAIL_HOSTNAME/$MAIL_HOSTNAME/g" /etc/postfix/main.cf
sed -i "s/\$MAIL_DOMAIN/$MAIL_DOMAIN/g" /etc/postfix/main.cf

# Set proper permissions
chmod 600 /etc/postfix/pgsql-*.cf
chown -R postfix:postfix /var/spool/postfix
chown -R vmail:mail /var/mail

# Create necessary directories
mkdir -p /var/spool/postfix/var/run/saslauthd
mkdir -p /var/spool/postfix/public
mkdir -p /var/spool/postfix/maildrop

# Generate missing files
touch /etc/postfix/aliases
postalias /etc/postfix/aliases

# Generate DKIM keys if they don't exist
if [ ! -f /etc/opendkim/keys/$MAIL_DOMAIN/mail.private ]; then
    echo "Generating DKIM keys for $MAIL_DOMAIN..."
    mkdir -p /etc/opendkim/keys/$MAIL_DOMAIN
    opendkim-genkey -b 2048 -d $MAIL_DOMAIN -D /etc/opendkim/keys/$MAIL_DOMAIN -s mail -v
    echo ""
    echo "========================================="
    echo "DKIM DNS Record (add this to your DNS):"
    echo "========================================="
    cat /etc/opendkim/keys/$MAIL_DOMAIN/mail.txt
    echo "========================================="
    echo ""
fi

# Fix OpenDKIM permissions
chown -R root:opendkim /etc/opendkim
chmod -R 750 /etc/opendkim
chmod 640 /etc/opendkim/keys/$MAIL_DOMAIN/mail.private

echo "Postfix configured. Starting services..."

# Start services using supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
