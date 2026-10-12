"""Smoke test: exercises every API endpoint with the demo accounts.
Run after the platform has been initialised:   python tests/smoke_test.py"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import create_app
app = create_app(); c = app.test_client()
def login(e,p):
    r = c.post('/api/auth/login', json={"email":e,"password":p}); assert r.status_code==200, r.data
    return {"Authorization":"Bearer "+r.get_json()["token"]}
adm = login("admin@smartcity.ai","Admin@123"); cit = login("citizen@smartcity.ai","Citizen@123"); trf = login("traffic@smartcity.ai","Authority@123")
def get(path, h=adm, show=None):
    r = c.get(path, headers=h)
    ok = r.status_code==200
    print(("OK  " if ok else "FAIL"), r.status_code, path, len(r.data))
    if not ok: print("   ", r.data[:400])
    j = r.get_json(silent=True)
    if show and j: print("   ", json.dumps(show(j))[:600])
    return j
ov = get("/api/city/overview", show=lambda j: j["kpis"])
get("/api/city/areas")
get("/api/city/area/3", cit, show=lambda j: {k:j[k] for k in ("name","traffic","aqi","water","waste","accident")})
get("/api/predict/traffic?area_id=1", show=lambda j: {"cur":j["current"],"fc":j["forecast"][:6],"rank":j["ranking"][:3]})
get("/api/predict/aqi?area_id=18", show=lambda j: {"cur":j["current"],"tom":j["tomorrow"]})
get("/api/predict/accident?area_id=2", show=lambda j: {"cur":j["current"],"imp":j["importance"]})
r=c.post('/api/predict/accident/custom', json={"area_id":2,"hour":22,"traffic_index":90,"rain_mm":6,"visibility_km":3}, headers=adm); print(r.status_code, r.get_json())
get("/api/predict/electricity", show=lambda j: {k:j[k] for k in ("current","today_avg","tomorrow_avg","peak","change_pct")})
get("/api/predict/water?area_id=3", show=lambda j: {k:j[k] for k in ("today","tomorrow","change_pct","status")})
get("/api/predict/waste?area_id=4", show=lambda j: {k:j[k] for k in ("today","tomorrow","breakdown","status")})
get("/api/alerts", show=lambda j: [a["message"] for a in j["alerts"]][:6])
get("/api/notifications", trf)
for k in ["traffic","aqi","accident","electricity","water","waste","complaints","models"]:
    for p in ["daily","monthly"]:
        get(f"/api/reports/{k}?period={p}")
get("/api/reports/traffic?format=csv")
get("/api/complaints?sort=priority", trf, show=lambda j: len(j["complaints"]))
get("/api/complaints/stats", adm); get("/api/complaints/clusters", adm, show=lambda j: j["clusters"][:2])
r=c.post('/api/complaints', json={"text":"Garbage has been piling up near our apartment in HSR Layout for 4 days and it smells terrible"}, headers=cit); print(r.status_code, r.get_json()["analysis"])
cid=r.get_json()["complaint"]["id"]
r=c.put(f'/api/complaints/{cid}/status', json={"status":"In Progress","note":"Team dispatched"}, headers=login("waste@smartcity.ai","Authority@123")); print(r.status_code)
for q in ["What is the traffic condition in HSR?","Which areas have the highest waste generation?","How is the air quality in Peenya","accident risk at silk board","electricity demand tomorrow","city summary","water in my area"]:
    r=c.post('/api/assistant/chat', json={"message":q}, headers=cit); print(r.status_code, r.get_json()["answer"][:230])
get("/api/department/dashboard", trf, show=lambda j: {"d":j["department"]["name"],"c":j["complaints"],"keys":list(j["data"])})
for slug in ["pollution","water","electricity","waste"]:
    get(f"/api/department/dashboard?dept={slug}", adm, show=lambda j: list(j["data"]))
get("/api/admin/users"); get("/api/admin/datasets", show=lambda j:[(d["table"],d["rows"]) for d in j["datasets"]]); get("/api/admin/models", show=lambda j:[(m["module"],m.get("algorithm")) for m in j["models"]])
get("/api/admin/analytics"); get("/api/admin/datasets/traffic_data/export?limit=5")
print(c.get("/api/admin/users", headers=cit).status_code, "(expect 403)")
print(c.get("/api/city/overview").status_code, "(expect 401)")
