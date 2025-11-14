FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Postfix, PostgreSQL client, and Python
RUN apt-get update && apt-get install -y \
    postfix \
    postfix-pgsql \
    libsasl2-modules \
    sasl2-bin \
    supervisor \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for content filter
RUN pip3 install --no-cache-dir \
    psycopg2-binary==2.9.9 \
    cryptography==41.0.7 \
    pycryptodome==3.19.0

# Copy configuration files
COPY main.cf /etc/postfix/main.cf
COPY master.cf /etc/postfix/master.cf
COPY pgsql-virtual-mailbox-domains.cf /etc/postfix/
COPY pgsql-virtual-mailbox-maps.cf /etc/postfix/
COPY pgsql-virtual-alias-maps.cf /etc/postfix/
COPY sasl/smtpd.conf /etc/postfix/sasl/smtpd.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /entrypoint.sh

# Copy content filters, policy services, and crypto utilities
RUN mkdir -p /app
COPY encrypt_filter.py /usr/local/bin/encrypt_filter.py
COPY decrypt_filter.py /usr/local/bin/decrypt_filter.py
COPY consent_policy.py /usr/local/bin/consent_policy.py
COPY crypto_utils.py /app/crypto_utils.py

RUN chmod +x /entrypoint.sh /usr/local/bin/encrypt_filter.py /usr/local/bin/decrypt_filter.py /usr/local/bin/consent_policy.py

# Create mail user
RUN useradd -r -u 5000 -g mail -d /var/mail -s /sbin/nologin vmail

EXPOSE 25 587

CMD ["/entrypoint.sh"]
