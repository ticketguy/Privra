FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Postfix and PostgreSQL client
RUN apt-get update && apt-get install -y \
    postfix \
    postfix-pgsql \
    libsasl2-modules \
    sasl2-bin \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration files
COPY main.cf /etc/postfix/main.cf
COPY master.cf /etc/postfix/master.cf
COPY pgsql-virtual-mailbox-domains.cf /etc/postfix/
COPY pgsql-virtual-mailbox-maps.cf /etc/postfix/
COPY pgsql-virtual-alias-maps.cf /etc/postfix/
COPY sasl/smtpd.conf /etc/postfix/sasl/smtpd.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# Create mail user
RUN useradd -r -u 5000 -g mail -d /var/mail -s /sbin/nologin vmail

EXPOSE 25 587

CMD ["/entrypoint.sh"]
