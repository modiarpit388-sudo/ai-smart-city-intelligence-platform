"""Authentication endpoints."""
import re
from datetime import datetime, timedelta

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import generate_password_hash

from ..auth import auth_required, make_token, revoke_current_session
from ..extensions import db
from ..models import Citizen, Location, PendingRegistration, User
from ..services.password_policy import check_password
from ..services.otp import generate_otp, hash_otp, send_otp_email, smtp_configured, verify_otp

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.get("/areas")
def public_areas():
    """Public list of localities (used by the registration form)."""
    return jsonify(areas=[{"id": l.id, "name": l.name} for l in Location.query.order_by(Location.name)])


def _now():
    return datetime.now()


def _issue_otp(pending: PendingRegistration):
    """Generate a fresh OTP for a pending registration and email it. Returns (ok, error_response)."""
    cfg = current_app.config
    otp = generate_otp()
    pending.otp_hash = hash_otp(pending.email, otp)
    pending.otp_expires_at = _now() + timedelta(minutes=cfg["OTP_EXPIRY_MINUTES"])
    pending.attempts = 0
    pending.last_sent_at = _now()
    db.session.commit()
    ok = send_otp_email(pending.email, pending.name, otp)
    if not ok:  # nothing was delivered, so don't make the user wait for the cooldown
        pending.last_sent_at = _now() - timedelta(seconds=cfg["OTP_RESEND_SECONDS"])
        db.session.commit()
    return ok


def _otp_payload(pending: PendingRegistration) -> dict:
    cfg = current_app.config
    return {"verification_required": True, "email": pending.email,
            "email_sent": smtp_configured(),  # False = server has no email provider set up (code only printed in its console)
            "expires_in": cfg["OTP_EXPIRY_MINUTES"] * 60, "resend_in": cfg["OTP_RESEND_SECONDS"]}


@bp.post("/register")
def register():
    """Step 1 – validate the form and email a one-time code. The account is created in /verify-otp."""
    d = request.get_json(force=True) or {}
    name, email, pw = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower(), d.get("password") or ""
    if len(name) < 2:
        return jsonify(error="Please enter your name"), 400
    if not EMAIL.match(email):
        return jsonify(error="Enter a valid email address"), 400
    if (msg := check_password(pw)):
        return jsonify(error=msg), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with this email already exists"), 409
    area = Location.query.get(d.get("area_id")) if d.get("area_id") else None

    pending = PendingRegistration.query.filter_by(email=email).first()
    if pending and (_now() - pending.last_sent_at).total_seconds() < current_app.config["OTP_RESEND_SECONDS"]:
        wait = int(current_app.config["OTP_RESEND_SECONDS"] - (_now() - pending.last_sent_at).total_seconds()) + 1
        return jsonify(error=f"A code was just sent. Please wait {wait}s before trying again.", retry_after=wait), 429
    if not pending:
        pending = PendingRegistration(email=email, otp_hash="", otp_expires_at=_now(), last_sent_at=_now(),
                                      name=name, password_hash="")
        db.session.add(pending)
    # (re)submitting the form just overwrites the pending details with the latest ones
    pending.name = name
    pending.password_hash = generate_password_hash(pw)
    pending.area_id = area.id if area else None
    pending.phone = d.get("phone")
    pending.address = d.get("address")

    if not _issue_otp(pending):
        return jsonify(error="We couldn't send the verification email. Please check the address and try again."), 502
    return jsonify(_otp_payload(pending)), 202


@bp.post("/resend-otp")
def resend_otp():
    email = ((request.get_json(force=True) or {}).get("email") or "").strip().lower()
    pending = PendingRegistration.query.filter_by(email=email).first()
    if not pending:
        return jsonify(error="No pending registration for this email. Please register again."), 404
    elapsed = (_now() - pending.last_sent_at).total_seconds()
    cooldown = current_app.config["OTP_RESEND_SECONDS"]
    if elapsed < cooldown:
        wait = int(cooldown - elapsed) + 1
        return jsonify(error=f"Please wait {wait}s before requesting another code.", retry_after=wait), 429
    if not _issue_otp(pending):
        return jsonify(error="We couldn't send the verification email. Please try again."), 502
    return jsonify(_otp_payload(pending))


@bp.post("/verify-otp")
def verify_otp_route():
    """Step 2 – check the code; on success create the user and sign them in."""
    d = request.get_json(force=True) or {}
    email, otp = (d.get("email") or "").strip().lower(), str(d.get("otp") or "").strip()
    cfg = current_app.config
    pending = PendingRegistration.query.filter_by(email=email).first()
    if not pending:
        return jsonify(error="No pending registration for this email. Please register again."), 404
    if _now() > pending.otp_expires_at:
        return jsonify(error="This code has expired. Request a new one.", code="otp_expired"), 400
    if pending.attempts >= cfg["OTP_MAX_ATTEMPTS"]:
        return jsonify(error="Too many incorrect attempts. Request a new code.", code="otp_locked"), 429
    if not (otp.isdigit() and len(otp) == cfg["OTP_LENGTH"]) or not verify_otp(email, otp, pending.otp_hash):
        pending.attempts += 1
        db.session.commit()
        left = cfg["OTP_MAX_ATTEMPTS"] - pending.attempts
        msg = "Incorrect code." + (f" {left} attempt{'s' if left != 1 else ''} left." if left > 0
                                  else " Too many attempts – request a new code.")
        return jsonify(error=msg, code="otp_invalid", attempts_left=left), 400

    if User.query.filter_by(email=email).first():  # registered meanwhile (race)
        db.session.delete(pending); db.session.commit()
        return jsonify(error="An account with this email already exists"), 409
    u = User(name=pending.name, email=email, role="citizen", area_id=pending.area_id,
             password_hash=pending.password_hash)
    db.session.add(u)
    db.session.flush()
    db.session.add(Citizen(user_id=u.id, phone=pending.phone, address=pending.address, home_area_id=u.area_id))
    db.session.delete(pending)
    db.session.commit()
    return jsonify(token=make_token(u), user=u.to_dict()), 201


@bp.post("/logout")
def logout():
    """Cancel this login's session key. Always answers OK (signing out twice, or with an old token, is harmless)."""
    revoke_current_session()
    return jsonify(ok=True)


@bp.post("/login")
def login():
    d = request.get_json(force=True) or {}
    u = User.query.filter_by(email=(d.get("email") or "").strip().lower()).first()
    if not u or not u.check_password(d.get("password") or ""):
        return jsonify(error="Invalid email or password"), 401
    if not u.is_active:
        return jsonify(error="This account has been deactivated"), 403
    return jsonify(token=make_token(u), user=u.to_dict())


@bp.get("/me")
@auth_required()
def me():
    return jsonify(user=g.user.to_dict())


@bp.put("/me")
@auth_required()
def update_me():
    d = request.get_json(force=True) or {}
    u = g.user
    if d.get("name"):
        u.name = d["name"].strip()
    if "area_id" in d and Location.query.get(d["area_id"]):
        u.area_id = d["area_id"]
    if d.get("password"):
        if (msg := check_password(d["password"])):
            return jsonify(error=msg), 400
        u.set_password(d["password"])
    db.session.commit()
    return jsonify(user=u.to_dict())
