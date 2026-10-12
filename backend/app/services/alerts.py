"""
AI alert engine – turns forecasts into human-readable alerts.

Rules (thresholds are deliberately simple and explainable):
  traffic     : >= 2 consecutive VERY-HIGH hours (index >= 80) in the next 6 h
  air quality : predicted AQI >= 180 within 24 h  (>= 250 => critical)
  accident    : predicted risk >= 75 % within 3 h
  waste       : tomorrow >= 15 % above the area's normal
  water       : tomorrow >= 12 % above the area's normal
  electricity : predicted peak >= 97th percentile of historical demand
  complaints  : >= 3 open HIGH-priority complaints in one area
Info alerts (city outlook) are always generated so the feed is never empty.
"""
import numpy as np
import pandas as pd

from ..extensions import db
from ..ml import forecast as F
from ..models import Alert, Complaint, Department, Notification, User
from ..services.ingest import read_sql
from ..services.insights import hlabel


def _dept(slug):
    d = Department.query.filter_by(slug=slug).first()
    return d.id if d else None


def _when(ts, now):
    ts = pd.Timestamp(ts)
    day = "today" if ts.date() == now.date() else "tomorrow" if ts.date() == (now + pd.Timedelta(days=1)).date() else ts.strftime("%a")
    return f"{day} {hlabel(ts)}"


def _windows(mask):
    """Contiguous True runs -> [(start, end)] indices."""
    out, s = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and s is None:
            s = i
        if not m and s is not None:
            out.append((s, i - 1))
            s = None
    return out


def build_candidates() -> list:
    A = F.areas()
    now = pd.Timestamp(F.latest_traffic()["ts"].max())
    tf, aq, ac = F.traffic_forecast(48), F.aqi_forecast(48), F.accident_forecast(12)
    wa, ws, el = F.water_forecast(7), F.waste_forecast(7), F.electricity_forecast(48)
    c = []

    # ---- traffic
    scored = []
    for i, a in A.iterrows():
        v = tf["values"][i, :6]
        for s, e in _windows(v >= 80):
            if e - s + 1 >= 2:
                scored.append((v[s:e + 1].max(), i, s, e))
    for mx, i, s, e in sorted(scored, reverse=True)[:6]:
        a, t0, t1 = A.iloc[i], tf["times"][s], tf["times"][e]
        c.append(dict(type="traffic", severity="critical" if e - s >= 3 else "warning", area=int(a["area_id"]), dept="traffic",
                      title=f"Heavy traffic at {a['name']}", key=f"traffic:{a['area_id']}:{t0:%Y%m%d%H}",
                      message=f"Heavy traffic predicted at {a['name']} between {hlabel(t0)} and {hlabel(t1 + pd.Timedelta(hours=1))} (peak index {mx:.0f}/100)."))

    # ---- AQI
    scored = [(aq["values"][i, :24].max(), i) for i in range(len(A)) if aq["values"][i, :24].max() >= 180]
    for mx, i in sorted(scored, reverse=True)[:5]:
        a, j = A.iloc[i], int(aq["values"][i, :24].argmax())
        c.append(dict(type="aqi", severity="critical" if mx >= 250 else "warning", area=int(a["area_id"]), dept="pollution",
                      title=f"Poor air quality at {a['name']}", key=f"aqi:{a['area_id']}:{aq['times'][j]:%Y%m%d%H}",
                      message=f"AQI predicted to reach {mx:.0f} at {a['name']} around {_when(aq['times'][j], now)}. Sensitive groups should limit outdoor activity."))

    # ---- accident
    scored = [(ac["risk"][i, :3].max(), i) for i in range(len(A)) if ac["risk"][i, :3].max() >= 75]
    for mx, i in sorted(scored, reverse=True)[:4]:
        a, j = A.iloc[i], int(ac["risk"][i, :3].argmax())
        c.append(dict(type="accident", severity="warning", area=int(a["area_id"]), dept="traffic",
                      title=f"High accident risk at {a['name']}", key=f"accident:{a['area_id']}:{ac['times'][j]:%Y%m%d%H}",
                      message=f"Accident risk predicted at {mx:.0f}% around {_when(ac['times'][j], now)} at {a['name']}. Consider extra patrolling."))

    # ---- waste & water (tomorrow vs. normal)
    tom = pd.Timestamp(ws["dates"][0])
    for i, a in A.iterrows():
        b = ws["history"].iloc[i, :-1].mean()
        if ws["values"][i, 0] >= 1.15 * b:
            c.append(dict(type="waste", severity="warning", area=int(a["area_id"]), dept="waste", title=f"Waste surge at {a['name']}",
                          key=f"waste:{a['area_id']}:{tom:%Y%m%d}",
                          message=f"Waste generation at {a['name']} predicted {(ws['values'][i, 0] / b - 1) * 100:.0f}% above normal ({ws['values'][i, 0]:.1f} tons). Schedule extra collection."))
        b = wa["history"].iloc[i, :-1].mean()
        if wa["values"][i, 0] >= 1.12 * b:
            c.append(dict(type="water", severity="info", area=int(a["area_id"]), dept="water", title=f"High water demand at {a['name']}",
                          key=f"water:{a['area_id']}:{tom:%Y%m%d}",
                          message=f"Water demand at {a['name']} expected {(wa['values'][i, 0] / b - 1) * 100:.0f}% above normal tomorrow."))
    tot_w, base_w = ws["values"][:, 0].sum(), ws["history"].iloc[:, :-1].mean(axis=1).sum()
    if tot_w >= 1.10 * base_w:
        c.append(dict(type="waste", severity="warning", area=None, dept="waste", title="City-wide waste above normal",
                      key=f"waste:city:{tom:%Y%m%d}", message=f"City waste generation predicted {(tot_w / base_w - 1) * 100:.0f}% above normal tomorrow ({tot_w:.0f} tons)."))

    # ---- electricity
    q97 = float(read_sql("SELECT demand_mw FROM electricity_data")["demand_mw"].quantile(0.97))
    nxt = el["values"][:36]
    j = int(nxt.argmax())
    if nxt[j] >= q97:
        c.append(dict(type="electricity", severity="warning", area=None, dept="electricity", title="Peak electricity demand expected",
                      key=f"electricity:{el['times'][j]:%Y%m%d%H}",
                      message=f"Demand may reach {nxt[j]:.0f} MW {_when(el['times'][j], now)} - above the 97th percentile ({q97:.0f} MW). Prepare reserve capacity."))

    # ---- complaint hotspots
    rows = db.session.query(Complaint.area_id, db.func.count(Complaint.id)).filter(
        Complaint.status != "Resolved", Complaint.priority == "HIGH").group_by(Complaint.area_id).all()
    names = {int(r["area_id"]): r["name"] for _, r in A.iterrows()}
    for aid, n in rows:
        if aid and n >= 3:
            c.append(dict(type="complaints", severity="warning", area=int(aid), dept=None, title=f"Complaint hotspot: {names.get(aid)}",
                          key=f"complaints:{aid}:{now:%Y%m%d}", message=f"{n} unresolved high-priority citizen complaints in {names.get(aid)}."))

    # ---- always-on outlook alerts
    cw = tf["values"][:, :12].mean(axis=0)
    j = int(cw.argmax())
    c.append(dict(type="traffic", severity="info", area=None, dept="traffic", title="City traffic outlook",
                  key=f"traffic:outlook:{now:%Y%m%d%H}", message=f"City-wide congestion expected to peak around {_when(tf['times'][j], now)} (avg index {cw[j]:.0f}/100)."))
    ca = aq["values"][:, :24].mean(axis=0)
    j = int(ca.argmax())
    c.append(dict(type="aqi", severity="info", area=None, dept="pollution", title="City air-quality outlook",
                  key=f"aqi:outlook:{now:%Y%m%d%H}", message=f"City average AQI expected to peak near {ca[j]:.0f} around {_when(aq['times'][j], now)}."))
    return c


def refresh_alerts() -> dict:
    """Recompute alerts, keep unchanged ones, retire stale ones, notify on new ones."""
    cands = build_candidates()
    existing = {a.dedupe_key: a for a in Alert.query.filter_by(is_active=True).all()}
    seen, created = set(), 0
    citizens = User.query.filter_by(role="citizen", is_active=True).all()
    officers = User.query.filter_by(role="authority", is_active=True).all()
    for cd in cands:
        seen.add(cd["key"])
        if cd["key"] in existing:
            a = existing[cd["key"]]
            a.message, a.severity = cd["message"], cd["severity"]
            continue
        a = Alert(type=cd["type"], severity=cd["severity"], title=cd["title"], message=cd["message"], location_id=cd["area"],
                  department_id=_dept(cd["dept"]) if cd["dept"] else None, dedupe_key=cd["key"])
        db.session.add(a)
        db.session.flush()
        created += 1
        if cd["severity"] == "info":
            continue
        for u in officers:
            if a.department_id is None or u.department_id == a.department_id:
                db.session.add(Notification(user_id=u.id, alert_id=a.id, title=a.title, message=a.message, severity=a.severity))
        for u in citizens:
            if cd["area"] is not None and u.area_id == cd["area"]:
                db.session.add(Notification(user_id=u.id, alert_id=a.id, title=a.title, message=a.message, severity=a.severity))
    for k, a in existing.items():
        if k not in seen:
            a.is_active = False
    db.session.commit()
    return {"active": len(seen), "created": created}
