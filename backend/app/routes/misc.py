"""Alerts, notifications, AI assistant, reports and the department portal."""
from flask import Blueprint, Response, g, jsonify, request

from ..auth import auth_required
from ..extensions import db
from ..models import Alert, Complaint, Department, Notification
from ..services import insights as I
from ..services.alerts import refresh_alerts
from ..services.assistant import SUGGESTIONS, chat
from ..services.reports import KINDS, build_report, to_csv

bp = Blueprint("misc", __name__, url_prefix="/api")


# ------------------------------------------------------------------ alerts / notifications
@bp.get("/alerts")
@auth_required()
def alerts():
    q = Alert.query
    if request.args.get("all") != "1":
        q = q.filter_by(is_active=True)
    u = g.user
    if u.role == "authority" and u.department_id:
        q = q.filter((Alert.department_id == u.department_id) | (Alert.department_id.is_(None)))
    if u.role == "citizen" and u.area_id:
        q = q.filter((Alert.location_id == u.area_id) | (Alert.location_id.is_(None)))
    order = {"critical": 0, "warning": 1, "info": 2}
    items = sorted(q.order_by(Alert.created_at.desc()).limit(80).all(), key=lambda a: order.get(a.severity, 3))
    return jsonify(alerts=[a.to_dict() for a in items])


@bp.post("/alerts/refresh")
@auth_required("admin", "authority")
def alerts_refresh():
    return jsonify(refresh_alerts())


@bp.get("/notifications")
@auth_required()
def notifications():
    items = Notification.query.filter_by(user_id=g.user.id).order_by(Notification.created_at.desc()).limit(40).all()
    return jsonify(notifications=[n.to_dict() for n in items], unread=sum(not n.is_read for n in items))


@bp.post("/notifications/read")
@auth_required()
def notifications_read():
    Notification.query.filter_by(user_id=g.user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    return jsonify(ok=True)


# ------------------------------------------------------------------ assistant
@bp.post("/assistant/chat")
@auth_required()
def assistant():
    q = ((request.get_json(force=True) or {}).get("message") or "").strip()
    if not q:
        return jsonify(error="Ask me something about the city"), 400
    return jsonify(chat(q, g.user))


@bp.get("/assistant/suggestions")
@auth_required()
def suggestions():
    return jsonify(suggestions=SUGGESTIONS)


# ------------------------------------------------------------------ reports
@bp.get("/reports/<kind>")
@auth_required("admin", "authority")
def report(kind):
    if kind not in KINDS:
        return jsonify(error="Unknown report"), 404
    rep = build_report(kind, request.args.get("period", "daily"), request.args.get("area_id", type=int))
    if request.args.get("format") == "csv":
        return Response(to_csv(rep), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={kind}_{rep['period']}_report.csv"})
    return jsonify(rep)


@bp.get("/reports")
@auth_required("admin", "authority")
def report_kinds():
    return jsonify(reports=[{"key": k, "title": v} for k, v in KINDS.items()])


# ------------------------------------------------------------------ department portal
@bp.get("/department/dashboard")
@auth_required("authority", "admin")
def department_dashboard():
    u = g.user
    if u.role == "authority":
        dept = u.department
    else:
        dept = Department.query.filter_by(slug=request.args.get("dept", "traffic")).first()
    if not dept:
        return jsonify(error="No department assigned"), 400
    ov = I.overview()
    rows = ov["areas"]
    slug = dept.slug
    comps = Complaint.query.filter_by(department_id=dept.id)
    data = {}
    if slug == "traffic":
        top = max(rows, key=lambda r: r["traffic"]["peak_next6"])
        data = {"traffic": I.traffic_payload(top["id"]), "accident": I.accident_payload(max(rows, key=lambda r: r["accident"]["risk_pct"])["id"])}
    elif slug == "pollution":
        data = {"aqi": I.aqi_payload(max(rows, key=lambda r: r["aqi"]["value"])["id"])}
    elif slug == "water":
        data = {"water": I.water_payload(max(rows, key=lambda r: r["water"]["today"])["id"])}
    elif slug == "electricity":
        data = {"electricity": I.electricity_payload()}
    elif slug == "waste":
        data = {"waste": I.waste_payload(max(rows, key=lambda r: r["waste"]["tomorrow"])["id"])}
    alerts = Alert.query.filter_by(is_active=True).filter((Alert.department_id == dept.id) | (Alert.department_id.is_(None))).limit(8).all()
    return jsonify(department=dept.to_dict(), kpis=ov["kpis"], areas=rows, data=data,
                   complaints={"pending": comps.filter(Complaint.status != "Resolved").count(),
                               "high": comps.filter(Complaint.status != "Resolved", Complaint.priority == "HIGH").count(),
                               "resolved": comps.filter(Complaint.status == "Resolved").count()},
                   alerts=[a.to_dict() for a in alerts])
