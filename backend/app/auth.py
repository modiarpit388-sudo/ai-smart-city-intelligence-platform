"""JWT authentication + role based access control."""
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from .models import User


def make_token(user: User) -> str:
    payload = {"sub": str(user.id), "role": user.role,
               "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXPIRE_HOURS"])}
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def _user_from_request():
    h = request.headers.get("Authorization", "")
    token = h[7:] if h.startswith("Bearer ") else request.args.get("token")
    if not token:
        return None
    try:
        data = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
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
