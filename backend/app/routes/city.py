"""City monitoring + AI prediction endpoints."""
from flask import Blueprint, g, jsonify, request

from ..auth import auth_required
from ..ml.forecast import ModelNotReady
from ..models import Location
from ..services import insights as I

bp = Blueprint("city", __name__, url_prefix="/api")


@bp.errorhandler(ModelNotReady)
def _not_ready(e):
    return jsonify(error=str(e), code="model_not_ready"), 503


@bp.errorhandler(KeyError)
def _nf(e):
    return jsonify(error="Not found"), 404


def _area(default_home=True):
    aid = request.args.get("area_id", type=int)
    if aid:
        return aid
    u = g.user
    if default_home and u.area_id:
        return u.area_id
    return Location.query.filter_by(name="Silk Board").first().id


@bp.get("/city/areas")
@auth_required()
def areas():
    return jsonify(areas=[l.to_dict() for l in Location.query.order_by(Location.name)])


@bp.get("/city/overview")
@auth_required()
def overview():
    return jsonify(I.overview())


@bp.get("/city/area/<int:area_id>")
@auth_required()
def area(area_id):
    return jsonify(I.area_detail(area_id))


@bp.get("/predict/traffic")
@auth_required()
def traffic():
    return jsonify(I.traffic_payload(_area()))


@bp.get("/predict/aqi")
@auth_required()
def aqi():
    return jsonify(I.aqi_payload(_area()))


@bp.get("/predict/accident")
@auth_required()
def accident():
    return jsonify(I.accident_payload(_area()))


@bp.post("/predict/accident/custom")
@auth_required()
def accident_custom():
    d = request.get_json(force=True) or {}
    d.setdefault("area_id", _area())
    return jsonify(I.accident_custom(d))


@bp.get("/predict/electricity")
@auth_required()
def electricity():
    return jsonify(I.electricity_payload())


@bp.get("/predict/water")
@auth_required()
def water():
    return jsonify(I.water_payload(_area()))


@bp.get("/predict/waste")
@auth_required()
def waste():
    return jsonify(I.waste_payload(_area()))
