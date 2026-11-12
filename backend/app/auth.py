"""JWT authentication + role based access control."""
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from .extensions import db
from .models import RevokedSession, User


def make_token(user: User) -> str:
    # "jti" = this login's own session key. Logging out revokes it, so the token can never be used again.
    payload = {"sub": str(user.id), "role": user.role, "sid": current_app.config["SESSION_KEY"], "jti": secrets.token_hex(16),
               "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXPIRE_HOURS"])}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _token_from_request():
    h = request.headers.get("Authorization", "")
    return h[7:] if h.startswith("Bearer ") else request.args.get("token")


def revoke_current_session() -> bool:
    """Sign out: blacklist the session key (jti) of the token in this request."""
    token = _token_from_request()
    if not token:
        return False
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
    except Exception:
        return False
    jti = data.get("jti")
    if jti and not db.session.get(RevokedSession, jti):
        db.session.add(RevokedSession(jti=jti, expires_at=datetime.fromtimestamp(data["exp"], timezone.utc).replace(tzinfo=None)))
    # housekeeping: forget sessions whose tokens have expired anyway
    RevokedSession.query.filter(RevokedSession.expires_at < datetime.utcnow()).delete()
    db.session.commit()
    return True


def _user_from_request():
    token = _token_from_request()
    if not token:
        return None
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        if data.get("sid") != current_app.config["SESSION_KEY"]:  # session key rotated -> old logins are void
            return None
        if data.get("jti") and db.session.get(RevokedSession, data["jti"]):  # signed out
            return None
        u = User.query.get(int(data["sub"]))
        return u if u and u.is_active else None
    except Exception:
        return None


def current_user():
    return getattr(g, "user", None) or _user_from_request()


def auth_required(*roles):
    """Usage: @auth_required()  |  @auth_required('admin')  |  @auth_required('admin','authority')"""
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            u = _user_from_request()
            if not u:
                return jsonify(error="Authentication required"), 401
            if roles and u.role not in roles:
                return jsonify(error="You do not have permission for this action"), 403
            g.user = u
            return fn(*a, **kw)
        return wrapper
    return deco
