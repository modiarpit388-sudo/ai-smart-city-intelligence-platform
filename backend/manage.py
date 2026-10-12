"""Maintenance commands:
   python manage.py init      create tables, seed, ingest, train (idempotent)
   python manage.py train     retrain every ML model
   python manage.py ingest    catch the data up to the current hour
   python manage.py reset     delete database + models and rebuild everything
"""
import os
import shutil
import sys

from app import create_app, init_platform
from app.config import Config, INSTANCE_DIR


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "reset":
        for p in (os.path.join(INSTANCE_DIR, "smartcity.db"), Config.MODEL_DIR):
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.remove(p)
        cmd = "init"
    app = create_app()
    if cmd == "init":
        init_platform(app)
    elif cmd == "train":
        from app.ml import trainer
        with app.app_context():
            trainer.train_all()
    elif cmd == "ingest":
        from app.services.ingest import ensure_data_current
        with app.app_context():
            print(ensure_data_current(True))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
