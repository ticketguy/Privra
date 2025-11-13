# Privra Webmail

Simple, fast webmail client for Privra Mail Server.

## Features

- ✅ **Login** with your email credentials
- ✅ **View Inbox** - See all your emails
- ✅ **Read Emails** - View full email content
- ✅ **Compose & Send** - Write and send new emails
- ✅ **Clean UI** - Simple, fast interface
- ✅ **Mobile Friendly** - Works on all devices

## Access

Once deployed, access webmail at:

```
https://mail.yourdomain.com/mail
```

## Login

Use your email credentials:
- **Email**: your-email@yourdomain.com
- **Password**: Your email password

## How It Works

The webmail client connects directly to:
- **Dovecot** (IMAP) for reading emails
- **Postfix** (SMTP) for sending emails

All connections are internal within the Docker network, ensuring security and speed.

## Technology Stack

- **Flask** - Python web framework
- **imaplib** - IMAP client for reading emails
- **smtplib** - SMTP client for sending emails
- **Pure HTML/CSS** - No JavaScript, fast and simple

## Development

Run locally:
```bash
cd webmail
pip install -r requirements.txt
export IMAP_HOST=dovecot
export SMTP_HOST=postfix
export SECRET_KEY=your-secret-key
python app.py
```

Access at: http://localhost:5001

## Configuration

Environment variables:
- `IMAP_HOST` - Dovecot hostname (default: dovecot)
- `IMAP_PORT` - IMAP port (default: 993)
- `SMTP_HOST` - Postfix hostname (default: postfix)
- `SMTP_PORT` - SMTP port (default: 587)
- `SECRET_KEY` - Flask secret key for sessions

## Security

- All sessions are encrypted
- Passwords are never stored, only used for authentication
- All mail connections use SSL/TLS
- Session timeout: 24 hours

## Troubleshooting

### Can't login
- Verify email credentials work with manual IMAP test
- Check Dovecot logs: `docker compose logs dovecot`

### Can't send emails
- Check Postfix logs: `docker compose logs postfix`
- Verify SMTP authentication is working

### Connection errors
- Ensure all services are running: `docker compose ps`
- Check network connectivity between containers
