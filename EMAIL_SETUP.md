# Sending the registration OTP to ANY email address

Run **one command** and answer the questions:

```
cd backend
python manage.py setupmail
```

Choose **1 (Brevo)** for reliable delivery to every Gmail / Outlook / Yahoo inbox.

## Brevo in 5 minutes (free, ~300 emails/day, no domain needed)
1. Sign up at https://www.brevo.com and confirm your email.
2. **Add a sender:** *Senders, Domains & Dedicated IPs → Senders → Add a sender*.
   Use your own Gmail address and click the confirmation link Brevo emails you.
3. **Create an API key:** top-right menu → *SMTP & API → API Keys → Generate a new API key*. It starts with `xkeysib-`.
4. Run `python manage.py setupmail`, choose 1, paste the sender email and the key.
5. `python run.py` → the first lines must say `📧 Email OTP: ON → sending through Brevo`.

If Brevo answers "unrecognised IP address": *Security → Authorised IPs* → deactivate the blocking.

Why not plain Gmail? Gmail is meant for personal mail; other people's inboxes often filter or delay messages sent
through it. Brevo uses trusted sending servers and, for free addresses like Gmail, sends with its own compliant
sender address, so the OTP arrives reliably. For a public launch, add your own domain in Brevo (DKIM/DMARC).
