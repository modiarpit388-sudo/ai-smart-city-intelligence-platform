"""Email OTP helpers: generate, hash, verify and send one-time passcodes."""
import hashlib
import hmac
import secrets
import socket
import smtplib
import ssl

import requests
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr

from flask import current_app


def generate_otp() -> str:
    """Cryptographically secure numeric code, e.g. '048213'."""
    n = current_app.config["OTP_LENGTH"]
    return f"{secrets.randbelow(10 ** n):0{n}d}"


def hash_otp(email: str, otp: str) -> str:
    """HMAC keyed with SECRET_KEY and bound to the email, so a DB leak does not reveal live codes."""
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, f"{email.lower()}:{otp}".encode(), hashlib.sha256).hexdigest()


def verify_otp(email: str, otp: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_otp(email, otp), stored_hash)


def _sender(cfg):
    """(display name, address) used in the From line."""
    name, addr = parseaddr(cfg["MAIL_FROM"])
    if cfg["MAIL_PROVIDER"] == "smtp":
        # A From address that differs from the login account is a classic spam signal (Gmail rewrites it anyway).
        if not addr or (cfg["SMTP_HOST"].lower().endswith("gmail.com") and addr.lower() != cfg["SMTP_USER"].lower()):
            addr = cfg["SMTP_USER"]
    return (name or "Smart City AI"), addr


def smtp_configured() -> bool:
    """True when real email can be sent (Brevo API or SMTP). Otherwise OTPs are only printed in the console (dev mode)."""
    c = current_app.config
    if c["MAIL_PROVIDER"] == "brevo":
        return bool(c["BREVO_API_KEY"] and _sender(c)[1] and "@" in _sender(c)[1])
    return bool(c["SMTP_HOST"] and c["SMTP_USER"] and c["SMTP_PASSWORD"])


def mail_status() -> str:
    """One-line description of how OTPs will be delivered (shown at server start)."""
    c = current_app.config
    from ..config import ENV_FILE, ENV_FILE_FOUND
    if smtp_configured():
        if c["MAIL_PROVIDER"] == "brevo":
            return f"📧 Email OTP: ON  → sending through Brevo as {_sender(c)[1]}"
        return f"📧 Email OTP: ON  → sending through {c['SMTP_HOST']}:{c['SMTP_PORT']} as {c['SMTP_USER']}"
    why = []
    if not ENV_FILE_FOUND:
        why.append(f"file not found: {ENV_FILE}")
    elif c["MAIL_PROVIDER"] == "brevo":
        if not c["BREVO_API_KEY"]: why.append("BREVO_API_KEY is empty")
        if not _sender(c)[1]: why.append("MAIL_FROM is empty")
    else:
        if not c["SMTP_HOST"]: why.append("SMTP_HOST is empty")
        if not c["SMTP_USER"]: why.append("SMTP_USER is empty")
        if not c["SMTP_PASSWORD"]: why.append("SMTP_PASSWORD is empty")
    return ("📧 Email OTP: OFF – codes will only be PRINTED in this window (" + "; ".join(why) + ").\n"
            "     Fix it by running:  python manage.py setupmail")


def _content(name: str, otp: str, minutes: int):
    text = (f"Hi {name},\n\nYour verification code for the AI Smart City Intelligence Platform is:\n\n"
            f"    {otp}\n\nIt expires in {minutes} minutes. If you did not try to register, you can ignore this email.\n")
    html = f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;max-width:480px;margin:auto;padding:24px;border:1px solid #e5e7eb;border-radius:12px">
  <h2 style="margin:0 0 8px;color:#0f172a">Verify your email</h2>
  <p style="color:#475569">Hi {name}, use this code to finish creating your Smart City AI account:</p>
  <div style="font-size:34px;letter-spacing:10px;font-weight:700;text-align:center;padding:16px;background:#f1f5f9;border-radius:10px;color:#0891b2">{otp}</div>
  <p style="color:#64748b;font-size:13px">This code expires in {minutes} minutes. If you didn't request it, ignore this email.</p>
</div>"""
    return text, html


# ------------------------------------------------------------------ Brevo (HTTPS API)
class MailAPIError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body}")
        self.status, self.body = status, body


def _send_brevo(cfg, to_email, name, subject, text, html):
    from_name, from_addr = _sender(cfg)
    r = requests.post(
        cfg["BREVO_API_URL"], timeout=20,
        headers={"api-key": cfg["BREVO_API_KEY"], "accept": "application/json", "content-type": "application/json"},
        json={"sender": {"name": from_name, "email": from_addr}, "to": [{"email": to_email, "name": name}],
              "subject": subject, "htmlContent": html, "textContent": text},
    )
    if r.status_code not in (200, 201, 202):
        raise MailAPIError(r.status_code, r.text[:400])


# ------------------------------------------------------------------ SMTP (e.g. Gmail)
def _deliver(msg, host, port, use_ssl, use_tls, user, password, debug=False):
    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=20, context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(host, port, timeout=20)
    if debug:
        server.set_debuglevel(1)
    with server:
        if not use_ssl and use_tls:
            server.starttls(context=ssl.create_default_context())
        if user:
            server.login(user, password)
        refused = server.send_message(msg)
        if refused:  # the server accepted the mail for some recipients but not others
            raise smtplib.SMTPRecipientsRefused(refused)


def _send_smtp(cfg, to_email, name, subject, text, html):
    from_name, from_addr = _sender(cfg)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_addr))
    msg["To"] = to_email
    msg["Reply-To"] = from_addr
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=from_addr.split("@")[-1])
    msg["Auto-Submitted"] = "auto-generated"          # tells mail systems this is a transactional message
    msg["X-Auto-Response-Suppress"] = "All"
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    host, user, pw = cfg["SMTP_HOST"], cfg["SMTP_USER"], cfg["SMTP_PASSWORD"]
    try:
        _deliver(msg, host, cfg["SMTP_PORT"], cfg["SMTP_USE_SSL"], cfg["SMTP_USE_TLS"], user, pw, cfg["SMTP_DEBUG"])
    except (OSError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected) as first:
        # Port 587 is sometimes blocked (college/office Wi-Fi, antivirus). Gmail also listens on 465 (SSL).
        if cfg["SMTP_USE_SSL"] or isinstance(first, socket.gaierror):
            raise
        print(f"  ⚠ port {cfg['SMTP_PORT']} failed ({first}); retrying on port 465 (SSL) ...", flush=True)
        _deliver(msg, host, 465, True, False, user, pw, cfg["SMTP_DEBUG"])


# ------------------------------------------------------------------ public entry point
def send_otp_email(to_email: str, name: str, otp: str) -> bool:
    """Send the OTP. Returns True on success. With no email provider configured it prints the code (dev mode)."""
    cfg = current_app.config
    minutes = cfg["OTP_EXPIRY_MINUTES"]

    if not smtp_configured():
        print(f"\n  📧 [DEV – email not configured] OTP for {to_email}: {otp}  (valid {minutes} min)\n", flush=True)
        return True

    text, html = _content(name, otp, minutes)
    subject = f"{otp} is your Smart City AI verification code"
    try:
        if cfg["MAIL_PROVIDER"] == "brevo":
            _send_brevo(cfg, to_email, name, subject, text, html)
            via = "Brevo"
        else:
            _send_smtp(cfg, to_email, name, subject, text, html)
            via = cfg["SMTP_HOST"]
        print(f"  ✔ Email accepted by {via} for delivery to {to_email}  (if it is not in their Inbox, check Spam / Promotions)", flush=True)
        return True
    except Exception as e:  # noqa
        current_app.logger.error("OTP email to %s failed: %s", to_email, e)
        if cfg["MAIL_PROVIDER"] == "brevo":
            used = (f"MAIL_PROVIDER=brevo  BREVO_API_KEY={cfg['BREVO_API_KEY'][:8]}...({len(cfg['BREVO_API_KEY'])} chars)  "
                    f"sender={_sender(cfg)[1]!r}")
        else:
            used = (f"SMTP_HOST={cfg['SMTP_HOST']!r}  SMTP_PORT={cfg['SMTP_PORT']}  SMTP_USER={cfg['SMTP_USER']!r}  "
                    f"SMTP_PASSWORD={'*' * len(cfg['SMTP_PASSWORD'])} ({len(cfg['SMTP_PASSWORD'])} chars)")
        print(f"\n  ❌ Could not send email to {to_email}: {type(e).__name__}: {e}\n"
              f"     Settings read from .env -> {used}\n     {_hint(e, cfg)}\n", flush=True)
        return False


def _hint(e: Exception, cfg) -> str:
    if isinstance(e, MailAPIError):
        b = e.body.lower()
        if "ip" in b and ("unrecognised" in b or "unrecognized" in b or "authorised" in b or "authorized" in b):
            return ("HINT: Brevo blocks unknown IP addresses. In Brevo go to Security -> Authorised IPs and "
                    "deactivate the blocking (or add this computer's IP).")
        if e.status == 401:
            return "HINT: Brevo rejected the API key. Copy a fresh key (it starts with xkeysib-) into BREVO_API_KEY."
        if e.status == 400 and "sender" in b:
            return ("HINT: the sender address is not verified in Brevo. In Brevo: Senders, Domains & Dedicated IPs -> "
                    "Senders -> Add a sender -> confirm the email Brevo sends you. MAIL_FROM must be that exact address.")
        if e.status in (402, 429):
            return "HINT: Brevo's free daily limit (about 300 emails) is used up, or the account is not activated yet."
        return "HINT: see the Brevo message above."
    if isinstance(e, requests.exceptions.ConnectionError):
        return "HINT: could not reach the email service - check your internet connection / firewall."
    if isinstance(e, socket.gaierror):
        return (f"HINT: the server name {cfg['SMTP_HOST']!r} could not be found. SMTP_HOST must be exactly "
                f"smtp.gmail.com (for Gmail) - also check your internet connection.")
    if isinstance(e, smtplib.SMTPAuthenticationError):
        return ("HINT: Gmail rejected the login. Use a 16-character App Password (not your normal password), "
                "with no spaces, in SMTP_PASSWORD, and your full address in SMTP_USER.")
    if isinstance(e, smtplib.SMTPRecipientsRefused):
        return "HINT: the mail server refused this recipient address - check that the email address really exists."
    if isinstance(e, smtplib.SMTPDataError) or isinstance(e, smtplib.SMTPSenderRefused):
        return ("HINT: Gmail blocked the message (often a sending limit - Gmail allows about 500 mails/day - or it "
                "flagged the account). Check the Gmail inbox of the sending account for a 'Google security alert'.")
    if isinstance(e, (TimeoutError, ConnectionRefusedError, smtplib.SMTPConnectError)):
        return "HINT: could not connect. Check SMTP_PORT=587 and that a firewall/antivirus is not blocking port 587."
    return "HINT: run  python manage.py testmail you@example.com  for details."
