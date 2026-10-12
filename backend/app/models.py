"""
Database schema for the AI Smart City Intelligence Platform.

Groups
------
Identity      : users, citizens, admins, departments
Geography     : locations
Monitoring    : traffic_data, accident_data, air_quality, electricity_data,
                water_consumption, waste_data
Complaints    : complaint_categories, complaints, complaint_updates
AI outputs    : predictions, alerts, notifications
ML registry   : ml_models, model_metrics
"""
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


# --------------------------------------------------------------------------- identity
class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    icon = db.Column(db.String(8), default="🏛️")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "slug": self.slug, "icon": self.icon}


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="citizen")  # citizen | authority | admin
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    area_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=True)  # home area
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    department = db.relationship("Department")
    area = db.relationship("Location")

    def set_password(self, raw: str):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "department": self.department.to_dict() if self.department else None,
            "area_id": self.area_id,
            "area_name": self.area.name if self.area else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Citizen(db.Model):
    """Citizen profile (extends users where role == 'citizen')."""
    __tablename__ = "citizens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    home_area_id = db.Column(db.Integer, db.ForeignKey("locations.id"))


class Admin(db.Model):
    """Admin profile (extends users where role == 'admin')."""
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    access_level = db.Column(db.String(20), default="super")


# --------------------------------------------------------------------------- geography
class Location(db.Model):
    __tablename__ = "locations"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    population_k = db.Column(db.Float, default=50)  # thousands of residents served
    area_type = db.Column(db.String(20))  # residential | commercial | IT | industrial | mixed
    road_type = db.Column(db.String(20))  # local | arterial | highway | junction
    traffic_base = db.Column(db.Float, default=0.6)
    pollution_base = db.Column(db.Float, default=1.0)
    industrial_index = db.Column(db.Float, default=0.1)
    commercial_index = db.Column(db.Float, default=0.5)
    accident_hist = db.Column(db.Integer, default=20)  # historical accidents / year
    has_junction = db.Column(db.Boolean, default=False)
    aliases = db.Column(db.String(200), default="")

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "slug": self.slug, "lat": self.lat, "lng": self.lng,
            "population_k": self.population_k, "area_type": self.area_type, "road_type": self.road_type,
        }


# --------------------------------------------------------------------------- monitoring data
class TrafficData(db.Model):
    __tablename__ = "traffic_data"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    traffic_index = db.Column(db.Float)  # 0-100 traffic density
    vehicle_count = db.Column(db.Integer)
    avg_speed = db.Column(db.Float)  # km/h
    congestion_level = db.Column(db.String(12))
    prev_traffic_index = db.Column(db.Float)
    is_holiday = db.Column(db.Integer, default=0)
    day_of_week = db.Column(db.Integer)
    weather = db.Column(db.String(16))
    rain_mm = db.Column(db.Float)
    temperature = db.Column(db.Float)
    __table_args__ = (db.Index("ix_traffic_loc_ts", "location_id", "timestamp"),)


class AccidentData(db.Model):
    __tablename__ = "accident_data"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    traffic_index = db.Column(db.Float)
    road_code = db.Column(db.Integer)
    has_junction = db.Column(db.Integer)
    rain_mm = db.Column(db.Float)
    visibility_km = db.Column(db.Float)
    avg_speed = db.Column(db.Float)
    is_night = db.Column(db.Integer)
    hist_accidents = db.Column(db.Integer)
    risk_score = db.Column(db.Float)
    risk_level = db.Column(db.String(8))  # LOW | MEDIUM | HIGH
    accident_count = db.Column(db.Integer, default=0)
    __table_args__ = (db.Index("ix_acc_loc_ts", "location_id", "timestamp"),)


class AirQuality(db.Model):
    __tablename__ = "air_quality"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    pm25 = db.Column(db.Float)
    pm10 = db.Column(db.Float)
    co = db.Column(db.Float)
    no2 = db.Column(db.Float)
    so2 = db.Column(db.Float)
    o3 = db.Column(db.Float)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    wind_speed = db.Column(db.Float)
    rain_mm = db.Column(db.Float)
    traffic_index = db.Column(db.Float)
    aqi = db.Column(db.Float)
    category = db.Column(db.String(20))
    __table_args__ = (db.Index("ix_aq_loc_ts", "location_id", "timestamp"),)


class ElectricityData(db.Model):
    __tablename__ = "electricity_data"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    demand_mw = db.Column(db.Float)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    is_holiday = db.Column(db.Integer, default=0)


class WaterConsumption(db.Model):
    __tablename__ = "water_consumption"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    consumption_ml = db.Column(db.Float)  # million litres
    temp_max = db.Column(db.Float)
    rainfall_mm = db.Column(db.Float)
    is_holiday = db.Column(db.Integer, default=0)
    __table_args__ = (db.Index("ix_water_loc_date", "location_id", "date"),)


class WasteData(db.Model):
    __tablename__ = "waste_data"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"), nullable=False)
    organic_tons = db.Column(db.Float)
    plastic_tons = db.Column(db.Float)
    paper_tons = db.Column(db.Float)
    other_tons = db.Column(db.Float)
    total_tons = db.Column(db.Float)
    collected_tons = db.Column(db.Float)
    temp_max = db.Column(db.Float)
    rainfall_mm = db.Column(db.Float)
    is_holiday = db.Column(db.Integer, default=0)
    is_festival = db.Column(db.Integer, default=0)
    __table_args__ = (db.Index("ix_waste_loc_date", "location_id", "date"),)


# --------------------------------------------------------------------------- complaints
class ComplaintCategory(db.Model):
    __tablename__ = "complaint_categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    icon = db.Column(db.String(8), default="📢")
    department = db.relationship("Department")


class Complaint(db.Model):
    __tablename__ = "complaints"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("complaint_categories.id"))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    area_id = db.Column(db.Integer, db.ForeignKey("locations.id"))
    priority = db.Column(db.String(8), default="MEDIUM")
    priority_confidence = db.Column(db.Float)
    category_confidence = db.Column(db.Float)
    sentiment = db.Column(db.String(10))
    sentiment_score = db.Column(db.Float)
    keywords = db.Column(db.String(200))
    cluster_id = db.Column(db.Integer)
    status = db.Column(db.String(20), default="Submitted")  # Submitted|In Review|In Progress|Resolved|Rejected
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.now)
    resolved_at = db.Column(db.DateTime)

    user = db.relationship("User")
    category = db.relationship("ComplaintCategory")
    department = db.relationship("Department")
    area = db.relationship("Location")
    updates = db.relationship("ComplaintUpdate", backref="complaint", order_by="ComplaintUpdate.created_at")

    def to_dict(self, with_updates=False):
        d = {
            "id": self.id, "text": self.text,
            "category": self.category.name if self.category else None,
            "category_icon": self.category.icon if self.category else None,
            "department": self.department.name if self.department else None,
            "area_id": self.area_id, "area": self.area.name if self.area else None,
            "priority": self.priority, "sentiment": self.sentiment,
            "sentiment_score": self.sentiment_score,
            "keywords": [k for k in (self.keywords or "").split(",") if k],
            "cluster_id": self.cluster_id, "status": self.status,
            "citizen": self.user.name if self.user else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
        if with_updates:
            d["updates"] = [u.to_dict() for u in self.updates]
        return d


class ComplaintUpdate(db.Model):
    __tablename__ = "complaint_updates"
    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=False)
    status = db.Column(db.String(20))
    note = db.Column(db.String(400))
    by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)
    by_user = db.relationship("User")

    def to_dict(self):
        return {"status": self.status, "note": self.note,
                "by": self.by_user.name if self.by_user else "System",
                "created_at": self.created_at.isoformat()}


# --------------------------------------------------------------------------- AI outputs
class Prediction(db.Model):
    """Latest forecast snapshot written by the prediction service."""
    __tablename__ = "predictions"
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(24), index=True)
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"))
    target_time = db.Column(db.DateTime)
    value = db.Column(db.Float)
    label = db.Column(db.String(20))
    model_id = db.Column(db.Integer, db.ForeignKey("ml_models.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)


class Alert(db.Model):
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(24))  # traffic | aqi | waste | water | electricity | accident | complaints
    severity = db.Column(db.String(10))  # info | warning | critical
    title = db.Column(db.String(120))
    message = db.Column(db.String(400))
    location_id = db.Column(db.Integer, db.ForeignKey("locations.id"))
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    dedupe_key = db.Column(db.String(120), index=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    area = db.relationship("Location")
    department = db.relationship("Department")

    def to_dict(self):
        return {
            "id": self.id, "type": self.type, "severity": self.severity, "title": self.title,
            "message": self.message, "area_id": self.location_id,
            "area": self.area.name if self.area else "City-wide",
            "department": self.department.name if self.department else None,
            "is_active": self.is_active, "created_at": self.created_at.isoformat(),
        }


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    alert_id = db.Column(db.Integer, db.ForeignKey("alerts.id"), nullable=True)
    title = db.Column(db.String(120))
    message = db.Column(db.String(400))
    severity = db.Column(db.String(10), default="info")
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "message": self.message, "severity": self.severity,
                "is_read": self.is_read, "created_at": self.created_at.isoformat()}


# --------------------------------------------------------------------------- ML registry
class MLModel(db.Model):
    __tablename__ = "ml_models"
    id = db.Column(db.Integer, primary_key=True)
    module = db.Column(db.String(30), index=True)
    algorithm = db.Column(db.String(40))
    task = db.Column(db.String(20))  # regression | classification | clustering
    version = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=False)
    train_rows = db.Column(db.Integer)
    test_rows = db.Column(db.Integer)
    train_seconds = db.Column(db.Float)
    features = db.Column(db.Text)  # JSON list
    feature_importance = db.Column(db.Text)  # JSON dict
    sample = db.Column(db.Text)  # JSON – actual vs predicted / confusion matrix
    trained_at = db.Column(db.DateTime, default=datetime.now)
    metrics = db.relationship("ModelMetric", backref="model", cascade="all, delete-orphan")


class ModelMetric(db.Model):
    __tablename__ = "model_metrics"
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey("ml_models.id"), nullable=False)
    name = db.Column(db.String(30))
    value = db.Column(db.Float)
