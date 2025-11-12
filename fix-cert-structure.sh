#!/bin/bash
# Create certificate structure for TLS_FLAVOR=cert

cd certs

# Create cert.pem and key.pem that Mailu expects
ln -sf letsencrypt/live/mail.privra.xyz/fullchain.pem cert.pem
ln -sf letsencrypt/live/mail.privra.xyz/privkey.pem key.pem

echo "Certificate symlinks created:"
ls -lh cert.pem key.pem
