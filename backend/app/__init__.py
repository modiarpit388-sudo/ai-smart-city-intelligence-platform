"""AI Smart City Intelligence Platform – Flask application factory."""
import os
import threading
import time

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from .config import Config
from .extensions import db


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=None)
    app.config.from_object(Config)
    if config:
        app.config.update(config)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    from .routes import admin, auth, city, complaints, misc
    for m in (auth, city, complaints, misc, admin):
        app.register_blueprint(m.bp)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", service="AI Smart City Intelligence Platform")

    @app.errorhandler(404)
    def not_found(e):
        from flask import request
        if request.path.startswith("/api/"):
            return jsonify(error="Not found"), 404
        return _spa()

    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="Internal server error", detail=str(e)), 500

    def _spa():
        static = app.config["STATIC_DIR"]
        index = os.path.join(static, "index.html")
        if os.path.exists(index):
            return send_from_directory(static, "index.html")
        return jsonify(message="API is running. Build the frontend (npm run build) or start it with npm run dev."), 200

    @app.get("/")
    def index():
        return _spa()

    @app.get("/<path:path>")
    def assets(path):
        static = app.config["STATIC_DIR"]
        full = os.path.join(static, path)
        if os.path.isfile(full):
            return send_from_directory(static, path)
        return _spa()

    return app


def init_platform(app: Flask, verbose: bool = True):
    """Create tables, seed master data, ingest data, train missing models, build alerts."""
    from .ml import nlp, trainer
    from .models import Complaint, Location
    from .seed import seed_complaints, seed_master
    from .services.alerts import refresh_alerts
    from .services.ingest import ensure_data_current

    say = print if verbose else (lambda *a, **k: None)
    with app.app_context():
        db.create_all()
        if Location.query.count() == 0:
            say("▶ Seeding master data (localities, departments, users) ...")
            seed_master()
        say("▶ Checking monitoring data ...")
        ensure_data_current(verbose)
        missing = trainer.missing_modules()
        if missing:
            say(f"▶ Training ML models: {', '.join(missing)}  (first run only, ~1 minute)")
            trainer.train_many(missing)
        if Complaint.query.count() == 0:
            say("▶ Creating sample complaints (analysed by the NLP engine) ...")
            seed_complaints()
            nlp.train_clusters(log=lambda *_: None)
        say("▶ Generating AI alerts ...")
        refresh_alerts()
        say("✔ Platform ready.")


def start_scheduler(app: Flask, every_seconds: int = 300):
    """Background thread: keeps data current (new hour -> new readings) and refreshes alerts."""
    def loop():
        from .services.alerts import refresh_alerts
        from .services.ingest import ensure_data_current
        while True:
            time.sleep(every_seconds)
            try:
                with app.app_context():
                    added = ensure_data_current()
                    if any(added.values()):
                        refresh_alerts()
            except Exception as e:  # noqa
                print("scheduler error:", e)
    threading.Thread(target=loop, daemon=True).start()
