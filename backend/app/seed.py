"""Master-data seeding: departments, complaint categories, localities, demo users, sample complaints."""
import random
from datetime import datetime, timedelta

from .extensions import db
from .models import (Admin, Citizen, Complaint, ComplaintCategory, ComplaintUpdate, Department, Location, User)
from .simulation.areas import AREAS
from .simulation.complaints_data import make_complaints

DEPARTMENTS = [
    ("Traffic Department", "traffic", "🚦"),
    ("Pollution Department", "pollution", "🌫️"),
    ("Water Department", "water", "💧"),
    ("Electricity Department", "electricity", "⚡"),
    ("Waste Management", "waste", "🗑️"),
]

CATEGORIES = [
    ("Garbage", "waste", "🗑️"), ("Roads", "traffic", "🛣️"), ("Water", "water", "💧"),
    ("Electricity", "electricity", "⚡"), ("Traffic", "traffic", "🚦"), ("Street lights", "electricity", "💡"),
    ("Drainage", "water", "🌊"), ("Pollution", "pollution", "🌫️"), ("Public safety", "traffic", "🛡️"),
]

DEMO_PASSWORDS = {"admin": "Admin@123", "citizen": "Citizen@123", "authority": "Authority@123"}

SAMPLE_CITIZENS = ["Ananya Rao", "Rohit Sharma", "Priya Nair", "Karthik Gowda", "Sneha Reddy", "Arjun Menon",
                   "Divya Iyer", "Vikram Shetty", "Meera Patil", "Suresh Kumar", "Lakshmi Narayan",
                   "Imran Khan", "Pooja Hegde", "Naveen Raj"]


def _user(name, email, role, password, dept=None, area=None):
    u = User(name=name, email=email, role=role, department_id=dept.id if dept else None,
             area_id=area.id if area else None)
    u.set_password(password)
    db.session.add(u)
    db.session.flush()
    if role == "citizen":
        db.session.add(Citizen(user_id=u.id, home_area_id=area.id if area else None))
    if role == "admin":
        db.session.add(Admin(user_id=u.id))
    return u


def seed_master():
    depts = {}
    for name, slug, icon in DEPARTMENTS:
        d = Department(name=name, slug=slug, icon=icon)
        db.session.add(d)
        depts[slug] = d
    db.session.flush()
    for name, slug, icon in CATEGORIES:
        db.session.add(ComplaintCategory(name=name, department_id=depts[slug].id, icon=icon))
    for a in AREAS:
        db.session.add(Location(**a))
    db.session.flush()

    hsr = Location.query.filter_by(name="HSR Layout").first()
    _user("System Admin", "admin@smartcity.ai", "admin", DEMO_PASSWORDS["admin"])
    _user("Demo Citizen", "citizen@smartcity.ai", "citizen", DEMO_PASSWORDS["citizen"], area=hsr)
    for name, slug, icon in DEPARTMENTS:
        _user(f"{name} Officer", f"{slug}@smartcity.ai", "authority", DEMO_PASSWORDS["authority"], dept=depts[slug])
    locs = Location.query.all()
    rng = random.Random(3)
    for n in SAMPLE_CITIZENS:
        _user(n, n.lower().replace(" ", ".") + "@example.com", "citizen", DEMO_PASSWORDS["citizen"], area=rng.choice(locs))
    db.session.commit()


def seed_complaints(n: int = 240):
    """Create realistic complaint history and run every one through the NLP engine."""
    from .ml import nlp
    rng = random.Random(21)
    citizens = User.query.filter_by(role="citizen").all()
    authorities = User.query.filter_by(role="authority").all()
    cats = {c.name: c for c in ComplaintCategory.query.all()}
    now = datetime.now()
    for row in make_complaints(n, seed=99, noisy=False):
        u = rng.choice(citizens)
        a = nlp.analyze(row["text"], default_area_id=u.area_id)
        cat = cats[a["category"]]
        age_days = int(rng.triangular(0, 70, 8))
        created = now - timedelta(days=age_days, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))
        p_resolved = min(0.92, 0.25 + age_days / 35)
        r = rng.random()
        status = "Resolved" if r < p_resolved else rng.choice(["Submitted", "In Review", "In Progress"])
        c = Complaint(user_id=u.id, text=row["text"], category_id=cat.id, department_id=cat.department_id,
                      area_id=a["location"]["id"] if a["location"] else u.area_id, priority=a["priority"],
                      priority_confidence=a["priority_confidence"], category_confidence=a["category_confidence"],
                      sentiment=a["sentiment"], sentiment_score=a["sentiment_score"],
                      keywords=",".join(a["keywords"]), cluster_id=a["cluster_id"], status=status,
                      created_at=created, updated_at=created)
        db.session.add(c)
        db.session.flush()
        db.session.add(ComplaintUpdate(complaint_id=c.id, status="Submitted", note="Complaint received and analysed by AI",
                                       by_user_id=None, created_at=created))
        if status != "Submitted":
            officer = next((o for o in authorities if o.department_id == cat.department_id), None)
            steps = {"In Review": ["In Review"], "In Progress": ["In Review", "In Progress"],
                     "Resolved": ["In Review", "In Progress", "Resolved"]}[status]
            t = created
            for s in steps:
                t = t + timedelta(hours=rng.randint(2, 40))
                db.session.add(ComplaintUpdate(complaint_id=c.id, status=s, by_user_id=officer.id if officer else None,
                                               note={"In Review": "Assigned to field team", "In Progress": "Work started on site",
                                                     "Resolved": "Issue fixed and verified"}[s], created_at=min(t, now)))
            c.updated_at = min(t, now)
            if status == "Resolved":
                c.resolved_at = min(t, now)
    db.session.commit()
