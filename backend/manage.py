"""Maintenance commands:
   python manage.py init      create tables, seed, ingest, train (idempotent)
   python manage.py train     retrain every ML model
   python manage.py ingest    catch the data up to the current hour
   python manage.py setupmail        choose Brevo or Gmail and write backend/.env for you (recommended)
   python manage.py testmail EMAIL   send a test OTP email to check your SMTP settings
   python manage.py reset     delete database + models and rebuild everything
"""
import os
import shutil
import sys

from app import create_app, init_platform
from app.config import Config, INSTANCE_DIR


def setup_mail():
    """Interactive helper: writes the email settings into backend/.env with no chance of typing them on the wrong line."""
    from app.config import ENV_FILE
    print("\n=== Email (OTP) setup ===")
    print("How should the app send emails?")
    print("  1) Brevo  (RECOMMENDED - free, reaches any Gmail/Outlook/Yahoo inbox reliably, no domain needed)")
    print("  2) Gmail  (works for testing, but other people's inboxes may filter it)\n")
    choice = (input("Choose 1 or 2 [1]: ").strip() or "1")

    if choice == "2":
        print("\nYou need a Gmail address and a 16-character *App Password*:")
        print("  https://myaccount.google.com/security (turn on 2-Step Verification), then")
        print("  https://myaccount.google.com/apppasswords\n")
        user = input("Your Gmail address            : ").strip()
        pw = input("App password (16 chars, paste) : ").strip().replace(" ", "")
        if "@" not in user or len(pw) < 12:
            print("✖ That doesn't look right (need a full email address and the 16-character app password). Nothing was saved.")
            return
        values = {"MAIL_PROVIDER": "smtp", "SMTP_HOST": "smtp.gmail.com", "SMTP_PORT": "587", "SMTP_USE_TLS": "true",
                  "SMTP_USE_SSL": "false", "SMTP_USER": user, "SMTP_PASSWORD": pw, "MAIL_FROM": f"Smart City AI <{user}>"}
        test_to = user
    else:
        print("\nBrevo setup (about 5 minutes, free):")
        print("  1. Sign up at https://www.brevo.com  (use your Gmail) and verify your email.")
        print("  2. Add a sender: Brevo -> 'Senders, Domains & Dedicated IPs' -> Senders -> Add a sender.")
        print("     Use your Gmail address, then click the confirmation link Brevo emails you.")
        print("  3. Get an API key: top-right menu -> 'SMTP & API' -> API Keys -> Generate a new API key.")
        print("     (The key starts with  xkeysib-  )\n")
        sender = input("Sender email you verified in Brevo : ").strip()
        key = input("Brevo API key (xkeysib-...)          : ").strip()
        if "@" not in sender or len(key) < 20:
            print("✖ That doesn't look right (need the verified sender email and the long API key). Nothing was saved.")
            return
        values = {"MAIL_PROVIDER": "brevo", "BREVO_API_KEY": key, "MAIL_FROM": f"Smart City AI <{sender}>"}
        test_to = sender

    lines = open(ENV_FILE, encoding="utf-8-sig").read().splitlines() if os.path.isfile(ENV_FILE) else []
    seen, out = set(), []
    for ln in lines:
        key_ = ln.split("=", 1)[0].strip()
        if "=" in ln and not ln.lstrip().startswith("#") and key_ in values:
            if key_ not in seen:
                out.append(f"{key_}={values[key_]}"); seen.add(key_)
            continue
        out.append(ln)
    out += [f"{k}={v}" for k, v in values.items() if k not in seen]
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"\n✔ Saved to {ENV_FILE}\nNow sending a test email to {test_to} ...\n")
    import subprocess  # (a list of args avoids Windows quoting problems that os.system has)
    subprocess.run([sys.executable, os.path.abspath(__file__), "testmail", test_to])


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "reset":
        for p in (os.path.join(INSTANCE_DIR, "smartcity.db"), Config.MODEL_DIR):
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.remove(p)
        cmd = "init"
    if cmd == "setupmail":
        return setup_mail()
    app = create_app()
    if cmd == "init":
        init_platform(app)
    elif cmd == "train":
        from app.ml import trainer
        with app.app_context():
            trainer.train_all()
    elif cmd == "ingest":
        from app.services.ingest import ensure_data_current
        with app.app_context():
            print(ensure_data_current(True))
    elif cmd == "testmail":
        to = sys.argv[2] if len(sys.argv) > 2 else None
        if not to:
            print("Usage: python manage.py testmail you@example.com"); return
        from app.services.otp import send_otp_email, smtp_configured
        with app.app_context():
            if not smtp_configured():
                print("✖ Email is not configured yet. Run:  python manage.py setupmail")
                return
            c = app.config
            print("Sending test email via " + ("Brevo API" if c["MAIL_PROVIDER"] == "brevo" else f"{c['SMTP_HOST']}:{c['SMTP_PORT']} as {c['SMTP_USER']}") + " ...")
            ok = send_otp_email(to, "Tester", "123456")
            if ok:
                print(f"✔ Sent! Check the inbox (and the Spam folder) of {to}. The subject is '123456 is your Smart City AI verification code'.")
            else:
                print("✖ Failed – read the ❌ message above; it says what to fix.")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
