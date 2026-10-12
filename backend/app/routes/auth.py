"""Authentication endpoints."""
import re

from flask import Blueprint, g, jsonify, request

from ..auth import auth_required, make_token
from ..extensions import db
from ..models import Citizen, Location, User

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.get("/areas")
def public_areas():
    """Public list of localities (used by the registration form)."""
    return jsonify(areas=[{"id": l.id, "name": l.name} for l in Location.query.order_by(Location.name)])


@bp.post("/register")
def register():
    d = request.get_json(force=True) or {}
    name, email, pw = (d.get("name") or "").strip(), (d.get("email") or "").strip().lower(), d.get("password") or ""
    if len(name) < 2:
        return jsonify(error="Please enter your name"), 400
    if not EMAIL.match(email):
        return jsonify(error="Enter a valid email address"), 400
    if len(pw) < 6:
        return jsonify(error="Password must be at least 6 characters"), 400
    if User.query.filter_by(email=email).first():
        return jsonify(error="An account with this email already exists"), 409
    area = Location.query.get(d.get("area_id")) if d.get("area_id") else None
    u = User(name=name, email=email, role="citizen", area_id=area.id if area else None)
    u.set_password(pw)
    db.session.add(u)
    db.session.flush()
    db.session.add(Citizen(user_id=u.id, phone=d.get("phone"), address=d.get("address"), home_area_id=u.area_id))
    db.session.commit()
    return jsonify(token=make_token(u), user=u.to_dict()), 201


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
        if len(d["password"]) < 6:
            return jsonify(error="Password must be at least 6 characters"), 400
        u.set_password(d["password"])
    db.session.commit()
    return jsonify(user=u.to_dict())
