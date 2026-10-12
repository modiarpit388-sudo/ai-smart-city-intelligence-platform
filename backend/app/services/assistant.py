"""
AI City Assistant.

Design principle: the assistant never invents city statistics.
  1. Understand the question (intent + locality) with keyword/gazetteer matching.
  2. Retrieve the real numbers from the database + ML forecasts  -> `facts`.
  3. Compose the answer from those facts.
     * default: rule-based natural-language templates (works offline)
     * if ANTHROPIC_API_KEY is set: an LLM rewrites the answer, but is told to use ONLY the facts.
"""
import json
import re

import requests
from flask import current_app

from ..ml import forecast as F
from ..ml.nlp import find_location
from ..models import Alert, Complaint, Location
from . import insights as I

INTENTS = [
    ("accident", r"accident|crash|risk|unsafe|safety"),
    ("traffic", r"traffic|jam|congest|commute|road condition|signal"),
    ("aqi", r"\baqi\b|air|pollut|smog|breath|pm2|pm 2"),
    ("water", r"water|supply|tap"),
    ("waste", r"waste|garbage|trash|rubbish|dustbin|litter"),
    ("electricity", r"electric|power|demand|load|\bmw\b|energy"),
    ("complaints", r"complaint|grievance"),
    ("alerts", r"alert|warning|notification"),
    ("overview", r"summary|overview|status|city|today|how is"),
]
RANK = r"highest|most|worst|top|which area|which areas|lowest|least|best|cleanest|rank|compare"
LOW_WORDS = r"lowest|least|best|cleanest"


def _detect_intent(q):
    ql = q.lower()
    for name, pat in INTENTS:
        if re.search(pat, ql):
            return name
    return "overview"


def _areas_sorted(rows, key, low=False, n=5):
    return sorted(rows, key=key, reverse=not low)[:n]


def _answer(intent, q, area, is_rank, low):
    ov = I.overview()
    rows = ov["areas"]
    k = ov["kpis"]
    facts, ans = {}, ""

    if intent == "traffic":
        if area and not is_rank:
            p = I.traffic_payload(area.id)
            pk = max(p["forecast"], key=lambda x: x["value"])
            nxt = ", ".join(f"{f['label']} → {f['level'].title()}" for f in p["forecast"][:4])
            facts = {"area": area.name, "current": p["current"], "peak": pk, "next_hours": p["forecast"][:6]}
            ans = (f"Traffic at {area.name} is currently {p['current']['level']} (index {p['current']['value']}/100, "
                   f"average speed {p['current']['speed']} km/h). Next hours: {nxt}. "
                   f"The model expects the peak of {pk['level']} ({pk['value']}/100) around {pk['label']}.")
        else:
            top = _areas_sorted(rows, lambda r: r["traffic"]["value"], low)
            facts = {"city_avg": k["traffic"], "ranking": [(r["name"], r["traffic"]["value"], r["traffic"]["level"]) for r in top]}
            ans = (f"City-wide traffic is {k['traffic']['level']} (average index {k['traffic']['value']}/100) with "
                   f"{k['traffic']['high_areas']} areas in HIGH congestion. "
                   f"{'Lightest' if low else 'Heaviest'}: " + "; ".join(f"{r['name']} {r['traffic']['level']} ({r['traffic']['value']})" for r in top[:4]) + ".")
    elif intent == "aqi":
        if area and not is_rank:
            p = I.aqi_payload(area.id)
            tm = ", ".join(f"{x['name']} {x['value']}" for x in p["tomorrow"])
            facts = {"area": area.name, "current": p["current"], "tomorrow": p["tomorrow"]}
            ans = (f"Air quality at {area.name} is {p['current']['category']} with AQI {p['current']['aqi']} "
                   f"(main pollutant: {p['current']['dominant'].upper()}). Tomorrow's outlook: {tm}.")
        else:
            top = _areas_sorted(rows, lambda r: r["aqi"]["value"], low)
            facts = {"city": k["aqi"], "ranking": [(r["name"], r["aqi"]["value"]) for r in top]}
            ans = (f"The city average AQI is {k['aqi']['value']} ({k['aqi']['category']}). "
                   f"{'Cleanest' if low else 'Most polluted'} areas: " + "; ".join(f"{r['name']} {r['aqi']['value']}" for r in top[:4]) + ".")
    elif intent == "water":
        if area and not is_rank:
            p = I.water_payload(area.id)
            facts = {"area": area.name, **{x: p[x] for x in ("today", "tomorrow", "change_pct", "status")}}
            ans = (f"Water consumption in {area.name} is {p['today']} million litres today (status {p['status']}); "
                   f"tomorrow it is forecast at {p['tomorrow']} ML ({p['change_pct']:+}%).")
        else:
            top = _areas_sorted(rows, lambda r: r["water"]["today"], low)
            facts = {"city": k["water"], "ranking": [(r["name"], r["water"]["today"]) for r in top]}
            ans = (f"City water consumption today is {k['water']['total_ml']} ML (status {k['water']['status']}); tomorrow ≈ {k['water']['tomorrow_ml']} ML. "
                   f"{'Lowest' if low else 'Highest'} demand: " + "; ".join(f"{r['name']} {r['water']['today']} ML" for r in top[:4]) + ".")
    elif intent == "waste":
        if area and not is_rank:
            p = I.waste_payload(area.id)
            bd = ", ".join(f"{a} {b} t" for a, b in p["breakdown"].items())
            facts = {"area": area.name, "today": p["today"], "tomorrow": p["tomorrow"], "breakdown": p["breakdown"], "status": p["status"]}
            ans = f"{area.name} is expected to generate {p['tomorrow']} tons of waste tomorrow ({p['status']} vs normal): {bd}."
        else:
            top = _areas_sorted(rows, lambda r: r["waste"]["tomorrow"], low)
            facts = {"city": k["waste"], "ranking": [(r["name"], r["waste"]["tomorrow"]) for r in top]}
            ans = (f"City waste: {k['waste']['total_tons']} tons today, ≈{k['waste']['tomorrow_tons']} tons tomorrow. "
                   f"{'Lowest' if low else 'Highest'} generation tomorrow: " + "; ".join(f"{r['name']} {r['waste']['tomorrow']} t" for r in top[:4]) + ".")
    elif intent == "electricity":
        p = I.electricity_payload()
        facts = {"current": p["current"], "today_avg": p["today_avg"], "tomorrow_avg": p["tomorrow_avg"], "peak": p["peak"]}
        ans = (f"Current demand is {p['current']['mw']:.0f} MW. Average today {p['today_avg']:.0f} MW, tomorrow {p['tomorrow_avg']:.0f} MW; "
               f"tomorrow's peak is forecast at {p['peak']['mw']:.0f} MW around {p['peak']['time']}.")
    elif intent == "accident":
        if area and not is_rank:
            p = I.accident_payload(area.id)
            facts = {"area": area.name, **p["current"]}
            ans = (f"Accident risk at {area.name} is {p['current']['level']} ({p['current']['risk_pct']}%). "
                   f"Main factors: {', '.join(p['current']['factors']).lower()}.")
        else:
            top = _areas_sorted(rows, lambda r: r["accident"]["risk_pct"], low)
            facts = {"ranking": [(r["name"], r["accident"]["risk_pct"], r["accident"]["level"]) for r in top]}
            ans = "Highest accident risk right now: " + "; ".join(f"{r['name']} {r['accident']['level']} ({r['accident']['risk_pct']}%)" for r in top[:4]) + "."
    elif intent == "complaints":
        open_ = Complaint.query.filter(Complaint.status != "Resolved").count()
        total = Complaint.query.count()
        high = Complaint.query.filter(Complaint.status != "Resolved", Complaint.priority == "HIGH").count()
        facts = {"total": total, "open": open_, "high_priority_open": high}
        ans = f"There are {total} complaints on record: {open_} still open, of which {high} are HIGH priority."
    elif intent == "alerts":
        al = Alert.query.filter_by(is_active=True).filter(Alert.severity != "info").order_by(Alert.created_at.desc()).limit(4).all()
        facts = {"alerts": [a.message for a in al]}
        ans = "Active alerts: " + " ".join(f"⚠ {a.message}" for a in al) if al else "There are no warning-level alerts right now."
    else:
        facts = {"kpis": k}
        ans = (f"City snapshot: traffic {k['traffic']['level']} ({k['traffic']['value']}/100), AQI {k['aqi']['value']} ({k['aqi']['category']}), "
               f"waste {k['waste']['total_tons']} t today, water {k['water']['total_ml']} ML ({k['water']['status']}), "
               f"electricity {k['electricity']['now_mw']:.0f} MW now (peak {k['electricity']['peak_mw']:.0f} MW at {k['electricity']['peak_time']}), "
               f"{k['alerts']} active alerts.")
    return ans, facts


def _llm(question, facts, draft):
    key = current_app.config.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=20,
                          headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                          json={"model": current_app.config["ANTHROPIC_MODEL"], "max_tokens": 350,
                                "system": "You are the AI City Assistant of a smart-city platform for Bengaluru. Answer the citizen's question in 2-4 friendly sentences. "
                                          "Use ONLY the numbers in the provided verified data. If the data does not answer the question, say so. Never invent statistics.",
                                "messages": [{"role": "user", "content": f"Question: {question}\n\nVerified data (JSON):\n{json.dumps(facts, default=str)}\n\nDraft answer:\n{draft}"}]})
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))
    except Exception:
        return None


SUGGESTIONS = ["What is the traffic condition in HSR Layout?", "Which areas have the highest waste generation?",
               "How is the air quality in Peenya?", "What is tomorrow's electricity demand?",
               "Accident risk at Silk Board?", "Give me a city summary"]


def chat(question: str, user=None) -> dict:
    q = question.strip()
    area = find_location(q)
    if area is None and user is not None and user.area_id and re.search(r"\bmy\b|\bhere\b|\bnearby\b|\bmy area\b", q.lower()):
        area = Location.query.get(user.area_id)
    intent = _detect_intent(q)
    is_rank = bool(re.search(RANK, q.lower())) and not (area and not re.search(r"which area|which areas|rank|compare", q.lower()))
    low = bool(re.search(LOW_WORDS, q.lower()))
    answer, facts = _answer(intent, q, area, is_rank, low)
    llm = _llm(q, facts, answer)
    return {"answer": llm or answer, "intent": intent, "area": area.name if area else None,
            "source": "llm+data" if llm else "data-rules", "facts": facts, "suggestions": SUGGESTIONS}
