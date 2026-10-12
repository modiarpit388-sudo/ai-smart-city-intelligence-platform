"""Citizen complaints with NLP analysis + workflow."""
from datetime import datetime

from flask import Blueprint, g, jsonify, request

from ..auth import auth_required
from ..extensions import db
from ..ml import nlp
from ..models import Complaint, ComplaintCategory, ComplaintUpdate, Notification

bp = Blueprint("complaints", __name__, url_prefix="/api/complaints")
STATUSES = ["Submitted", "In Review", "In Progress", "Resolved", "Rejected"]


def _visible(q):
    u = g.user
    if u.role == "citizen":
        return q.filter(Complaint.user_id == u.id)
    if u.role == "authority" and u.department_id:
        return q.filter(Complaint.department_id == u.department_id)
    return q


@bp.post("/analyze")
@auth_required()
def analyze():
    text = ((request.get_json(force=True) or {}).get("text") or "").strip()
    if len(text) < 8:
        return jsonify(error="Please describe the problem in a few words"), 400
    return jsonify(nlp.analyze(text, default_area_id=g.user.area_id))


@bp.post("")
@auth_required("citizen", "admin")
def create():
    d = request.get_json(force=True) or {}
    text = (d.get("text") or "").strip()
    if len(text) < 8:
        return jsonify(error="Please describe the problem in a few words"), 400
    a = nlp.analyze(text, default_area_id=g.user.area_id)
    cat = ComplaintCategory.query.filter_by(name=a["category"]).first()
    area_id = d.get("area_id") or (a["location"]["id"] if a["location"] else g.user.area_id)
    c = Complaint(user_id=g.user.id, text=text, category_id=cat.id, department_id=cat.department_id, area_id=area_id,
                  priority=a["priority"], priority_confidence=a["priority_confidence"], category_confidence=a["category_confidence"],
                  sentiment=a["sentiment"], sentiment_score=a["sentiment_score"], keywords=",".join(a["keywords"]),
                  cluster_id=a["cluster_id"], status="Submitted")
    db.session.add(c)
    db.session.flush()
    db.session.add(ComplaintUpdate(complaint_id=c.id, status="Submitted", note=f"Auto-routed to {cat.department.name} by AI", by_user_id=None))
    from ..models import User
    for o in User.query.filter_by(role="authority", department_id=cat.department_id, is_active=True):
        db.session.add(Notification(user_id=o.id, title=f"New {a['priority']} complaint: {a['category']}", message=text[:160],
                                    severity="warning" if a["priority"] == "HIGH" else "info"))
    db.session.commit()
    return jsonify(complaint=c.to_dict(True), analysis=a), 201


@bp.get("")
@auth_required()
def list_():
    q = _visible(Complaint.query)
    for f, col in (("status", Complaint.status), ("priority", Complaint.priority)):
        if request.args.get(f):
            q = q.filter(col == request.args[f])
    if request.args.get("category"):
        q = q.join(ComplaintCategory).filter(ComplaintCategory.name == request.args["category"])
    if request.args.get("area_id"):
        q = q.filter(Complaint.area_id == request.args.get("area_id", type=int))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    items = q.order_by(Complaint.created_at.desc()).limit(300).all()
    if request.args.get("sort") == "priority":
        items.sort(key=lambda c: (order.get(c.priority, 3), -c.created_at.timestamp()))
    return jsonify(complaints=[c.to_dict() for c in items])


@bp.get("/<int:cid>")
@auth_required()
def get(cid):
    c = _visible(Complaint.query).filter(Complaint.id == cid).first()
    if not c:
        return jsonify(error="Complaint not found"), 404
    return jsonify(complaint=c.to_dict(True))


@bp.put("/<int:cid>/status")
@auth_required("authority", "admin")
def set_status(cid):
    c = _visible(Complaint.query).filter(Complaint.id == cid).first()
    if not c:
        return jsonify(error="Complaint not found"), 404
    d = request.get_json(force=True) or {}
    st = d.get("status")
    if st not in STATUSES:
        return jsonify(error="Invalid status"), 400
    c.status, c.updated_at = st, datetime.now()
    c.resolved_at = datetime.now() if st == "Resolved" else None
    db.session.add(ComplaintUpdate(complaint_id=c.id, status=st, note=(d.get("note") or f"Status changed to {st}")[:400], by_user_id=g.user.id))
    db.session.add(Notification(user_id=c.user_id, title=f"Complaint #{c.id}: {st}", message=(d.get("note") or f"Your complaint is now '{st}'.")[:200],
                                severity="info"))
    db.session.commit()
    return jsonify(complaint=c.to_dict(True))


@bp.get("/stats")
@auth_required()
def stats():
    items = _visible(Complaint.query).all()
    by = lambda f: {k: sum(1 for c in items if f(c) == k) for k in {f(c) for c in items}}
    return jsonify(total=len(items), resolved=sum(c.status == "Resolved" for c in items),
                   pending=sum(c.status not in ("Resolved", "Rejected") for c in items),
                   by_status=by(lambda c: c.status), by_priority=by(lambda c: c.priority),
                   by_category=by(lambda c: c.category.name if c.category else "-"),
                   by_sentiment=by(lambda c: c.sentiment))


@bp.get("/clusters")
@auth_required("authority", "admin")
def clusters():
    items = _visible(Complaint.query).all()
    labels = nlp.cluster_labels()
    out = []
    for i, lab in enumerate(labels):
        m = [c for c in items if c.cluster_id == i]
        if not m:
            continue
        cats = {}
        for c in m:
            k = c.category.name if c.category else "-"
            cats[k] = cats.get(k, 0) + 1
        out.append({"id": i, "label": lab, "count": len(m), "pending": sum(c.status != "Resolved" for c in m),
                    "high": sum(c.priority == "HIGH" for c in m), "top_category": max(cats, key=cats.get),
                    "example": m[0].text[:140]})
    out.sort(key=lambda x: -x["count"])
    return jsonify(clusters=out)
