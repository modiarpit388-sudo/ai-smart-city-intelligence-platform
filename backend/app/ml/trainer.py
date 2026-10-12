"""Orchestrates (re)training of every module, optionally in a background thread."""
import threading
import time
from datetime import datetime

from . import nlp
from . import pipelines as P
from .forecast import clear_cache
from .registry import active_model, clear_model_cache, is_trained

NUMERIC = {
    "traffic": P.train_traffic, "accident": P.train_accident, "aqi": P.train_aqi,
    "electricity": P.train_electricity, "water": P.train_water, "waste": P.train_waste,
}
NLP_MODULES = ["complaint_category", "complaint_priority", "complaint_cluster"]
ALL_GROUPS = list(NUMERIC) + ["complaints"]

STATUS = {"running": False, "current": None, "log": [], "finished_at": None, "error": None}
_lock = threading.Lock()


def _log(msg):
    print(msg)
    STATUS["log"].append(f"{datetime.now():%H:%M:%S}  {msg}")
    STATUS["log"] = STATUS["log"][-200:]


def missing_modules() -> list:
    """Groups that have no trained model yet."""
    miss = [m for m in NUMERIC if not is_trained(m)]
    if not all(is_trained(m) for m in NLP_MODULES):
        miss.append("complaints")
    return miss


def train_group(group: str, log=_log):
    t0 = time.time()
    STATUS["current"] = group
    log(f"▶ Training {group} ...")
    if group == "complaints":
        nlp.train_nlp(log=log)
    elif group in NUMERIC:
        NUMERIC[group](log=log)
    else:
        raise ValueError(f"Unknown module '{group}'")
    log(f"  ({group} finished in {time.time() - t0:.1f}s)")


def train_many(groups, log=_log):
    for g in groups:
        train_group(g, log)
    clear_cache()


def train_all(log=_log):
    train_many(ALL_GROUPS, log)


def start_background(app, groups):
    """Kick off training in a daemon thread. Returns False if a job is already running."""
    with _lock:
        if STATUS["running"]:
            return False
        STATUS.update(running=True, current=None, error=None, log=[], finished_at=None)

    def job():
        with app.app_context():
            try:
                train_many(groups)
                clear_model_cache()
                from ..services.alerts import refresh_alerts
                refresh_alerts()
            except Exception as e:  # noqa
                STATUS["error"] = str(e)
                _log(f"✖ training failed: {e}")
            finally:
                STATUS.update(running=False, current=None, finished_at=datetime.now().isoformat())

    threading.Thread(target=job, daemon=True).start()
    return True
