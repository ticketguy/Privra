FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Dovecot and PostgreSQL client
RUN apt-get update && apt-get install -y \
    dovecot-core \
    dovecot-imapd \
    dovecot-lmtpd \
    dovecot-pgsql \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY dovecot.conf /etc/dovecot/dovecot.conf
COPY conf.d/ /etc/dovecot/conf.d/
COPY dovecot-sql.conf.ext /etc/dovecot/dovecot-sql.conf.ext
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Create mail user
RUN useradd -r -u 5000 -g mail -d /var/mail -s /sbin/nologin vmail

EXPOSE 143 993 12345 24

CMD ["/entrypoint.sh"]
