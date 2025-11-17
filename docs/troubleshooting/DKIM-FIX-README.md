# DKIM Signing Fix

## Problem
DKIM wasn't signing outgoing emails properly. The issue was that the Postfix reinject ports (used by content filters) weren't explicitly configured to use DKIM milters.

## Root Cause
When emails are processed through content filters (encrypt_filter.py and decrypt_filter.py), they are reinjected back into Postfix through special ports:
- **localhost:10026** - Incoming emails (internet → Privra users)
- **localhost:10027** - Outgoing emails (Privra users → internet)

These reinject ports had many security options disabled (for trust reasons), but they were also missing explicit milter configuration. While they should have inherited milter settings from main.cf, it's best practice to explicitly configure them.

## Solution
Added explicit DKIM milter configuration to both reinject ports in `postfix/master.cf`:

```
-o smtpd_milters=inet:localhost:8891
-o non_smtpd_milters=inet:localhost:8891
```

This ensures that:
1. **Outgoing emails** (port 10027) are signed with DKIM before being sent to external recipients
2. **Incoming emails** (port 10026) can have their DKIM signatures verified (though we don't reject based on DKIM failure)

## Email Flow with DKIM

### Outgoing Email (Privra → Internet)
1. User submits email via port 587 (submission)
2. Postfix applies `decrypt` content filter
3. `decrypt_filter.py` processes the email (decrypts if needed for external recipient)
4. Email is reinjected to **localhost:10027**
5. **DKIM signing happens here** via OpenDKIM milter on port 8891
6. Email is delivered to external recipient with DKIM signature

### Incoming Email (Internet → Privra)
1. External server connects to port 25 (smtp)
2. Postfix applies `encrypt` content filter
3. `encrypt_filter.py` processes the email (encrypts if for Privra user)
4. Email is reinjected to **localhost:10026**
5. DKIM verification happens here (if sender used DKIM)
6. Email is delivered to Dovecot/user mailbox

## Testing

After applying this fix, you need to:

1. **Rebuild and restart the Postfix container:**
   ```bash
   cd ~/privra-mail
   docker compose up -d --build postfix
   ```

2. **Send a test email to mail-tester.com:**
   - Log into your Privra webmail
   - Send an email to test-XXXXX@srv1.mail-tester.com (get the address from mail-tester.com)
   - Check the results on mail-tester.com
   - Look for "Your message is signed with DKIM" (should be green/passing)

3. **Check DKIM in email headers:**
   Send an email to Gmail and view the original message source. You should see:
   ```
   DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/simple; d=privra.xyz;
       s=mail; t=XXXXXXXXXX;
       bh=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX;
       h=From:To:Subject:Date;
       b=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
   ```

4. **Verify DNS record is still published:**
   ```bash
   host -t TXT mail._domainkey.privra.xyz
   ```
   Should return your DKIM public key.

## Expected Improvements

- **Mail-tester score:** Should improve from 7/10 to 8-9/10
- **Gmail/Outlook delivery:** Better inbox placement (less likely to go to spam)
- **Email authenticity:** Recipients can verify emails actually came from privra.xyz
- **Domain reputation:** Builds trust with email providers over time

## Troubleshooting

If DKIM still isn't working after the fix:

1. **Check if OpenDKIM is running:**
   ```bash
   docker compose exec postfix ps aux | grep opendkim
   ```

2. **Check DKIM logs:**
   ```bash
   docker compose logs postfix | grep -i dkim
   ```

3. **Verify DKIM keys exist:**
   ```bash
   docker compose exec postfix ls -la /etc/opendkim/keys/privra.xyz/
   ```

4. **Test DKIM socket:**
   ```bash
   docker compose exec postfix nc -zv localhost 8891
   ```

5. **Check Postfix milter config:**
   ```bash
   docker compose exec postfix postconf | grep milter
   ```

Should show:
```
milter_default_action = accept
milter_protocol = 6
non_smtpd_milters = inet:localhost:8891
smtpd_milters = inet:localhost:8891
```
