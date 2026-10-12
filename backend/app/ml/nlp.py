"""
Citizen-complaint NLP engine.

Pipeline for every complaint:
    text -> TF-IDF -> [category classifier]  -> Garbage / Roads / Water / ...
                   -> [priority classifier]  -> LOW / MEDIUM / HIGH   (+ safety keyword rules)
         -> lexicon sentiment                -> Negative / Neutral / Positive
         -> TF-IDF keyword extraction        -> top terms
         -> gazetteer location matching      -> locality (falls back to the citizen's home area)
         -> K-Means                          -> complaint group (finds recurring problems)
"""
import re
import time

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, silhouette_score
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
from sklearn.svm import LinearSVC

from ..extensions import db
from ..models import Complaint, Location
from ..simulation.complaints_data import make_complaints
from .registry import _store, classification_metrics, load_bundle, save_bundle

CATEGORIES = ["Garbage", "Roads", "Water", "Electricity", "Traffic", "Street lights", "Drainage", "Pollution",
              "Public safety"]
PRIORITIES = ["LOW", "MEDIUM", "HIGH"]

STRONG_CUES = ["accident", "injur", "dangerous", "urgent", "emergency", "sparking", "live wire", "fire",
               "burst", "health hazard", "unsafe", "critical", "collision", "gas leak", "toxic", "harass",
               "violence", "trapped", "fell sick", "life"]
NEG = ["garbage", "rotting", "smell", "stink", "dangerous", "unsafe", "terrible", "frustrating", "disappointed",
       "broken", "dirty", "blocked", "overflowing", "damaged", "bad", "worst", "angry", "pathetic", "not working",
       "delay", "suffering", "injured", "accident", "dark", "leak", "jam", "fail", "issue", "problem", "pothole",
       "sewage", "contaminated", "no water", "no electricity", "power cut", "toxic", "harassed", "fire"]
POS = ["thank", "thanks", "appreciate", "great", "good job", "helpful", "quick response", "resolved", "happy",
       "excellent", "well done", "satisfied"]
CUE_WORDS = {"fix", "soon", "inconvenience", "causing", "residents", "responded", "far", "possible", "emergency", "act",
             "immediately", "hazard", "health", "urgent", "dangerous", "minor", "issue", "hurry", "small", "problem",
             "mild", "complained", "nobody", "going", "people", "respond", "stop", "children", "elders", "injured",
             "extremely", "whenever", "problem", "having", "made", "come", "coming", "long", "time", "main", "corner",
             "street", "lane", "opposite", "close", "beside", "behind", "outside", "temple", "hospital", "market",
             "park", "school", "apartment", "bus", "stand"}
EXTRA_STOP = {"please", "kindly", "sir", "madam", "dear", "hello", "thank", "thanks", "complaint", "note",
              "action", "look", "need", "needed", "request", "requesting", "awaiting", "reply", "response",
              "quick", "take", "way", "near", "frustrating", "disappointed", "delay", "days", "day", "last",
              "past", "several", "hours", "morning", "evening"}


def _candidates():
    def tfidf():
        return TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True)
    return {
        "Logistic Regression": make_pipeline(tfidf(), LogisticRegression(max_iter=400, C=8)),
        "Linear SVM": make_pipeline(tfidf(), LinearSVC(C=1.0)),
        "Naive Bayes": make_pipeline(tfidf(), MultinomialNB(alpha=0.3)),
    }


# --------------------------------------------------------------------------- training
def _train_text_classifier(module, texts, labels, classes, held_out, log):
    """`held_out` marks complaints written from templates never seen in training, so the reported
    metrics measure generalisation to new wording (not memorisation of repeated sentences)."""
    t0 = time.time()
    y = np.array([classes.index(l) for l in labels])
    held_out = np.asarray(held_out, dtype=bool)
    Xtr = [t for t, h in zip(texts, held_out) if not h]
    Xte = [t for t, h in zip(texts, held_out) if h]
    ytr, yte = y[~held_out], y[held_out]
    results, fitted = {}, {}
    for name, est in _candidates().items():
        s = time.time()
        m = est.fit(Xtr, ytr)
        pred = m.predict(Xte)
        results[name] = {"metrics": classification_metrics(yte, pred), "seconds": time.time() - s}
        fitted[name] = (m, pred)
        log(f"      · {name:<20} acc={results[name]['metrics']['Accuracy']:.3f}  F1={results[name]['metrics']['F1']:.3f}")
    best = max(results, key=lambda k: results[k]["metrics"]["F1"])
    bm, bpred = fitted[best]
    cm = confusion_matrix(yte, bpred, labels=list(range(len(classes)))).tolist()
    # most influential words of the best (linear) model, for the "explainability" panel
    importance = {}
    try:
        vec, clf = bm.steps[0][1], bm.steps[-1][1]
        vocab = np.array(vec.get_feature_names_out())
        coefs = np.abs(clf.coef_).max(axis=0) if hasattr(clf, "coef_") else np.abs(clf.feature_log_prob_).max(axis=0)
        top = np.argsort(-coefs)[:12]
        tot = coefs[top].sum() or 1
        importance = {vocab[i]: float(round(coefs[i] / tot, 4)) for i in top}
    except Exception:
        pass
    final = _candidates()[best].fit(texts, y)
    save_bundle(module, {"model": final, "algorithm": best, "classes": classes, "task": "classification"})
    _store(module, "classification", results, best, ["tf-idf (1-2 grams)"], len(Xtr), len(Xte), importance,
           {"classes": classes, "confusion_matrix": cm}, time.time() - t0)
    log(f"   ✔ {module}: best = {best}")


def train_nlp(log=print):
    data = make_complaints(1800)
    texts = [d["text"] for d in data]
    # hold out: (a) sentences written from an unseen template, (b) ~12% of freely composed sentences
    held = [d["tpl"] == 3 or (d["tpl"] == -1 and i % 8 == 0) for i, d in enumerate(data)]
    _train_text_classifier("complaint_category", texts, [d["category"] for d in data], CATEGORIES, held, log)
    _train_text_classifier("complaint_priority", texts, [d["priority"] for d in data], PRIORITIES, held, log)
    train_clusters(log)


def train_clusters(log=print, k: int = 9):
    """K-Means on complaint texts (synthetic corpus + real complaints already in the DB)."""
    t0 = time.time()
    texts = [d["text"] for d in make_complaints(700, seed=11)]
    texts += [c.text for c in Complaint.query.limit(2000).all()]
    stop = list(ENGLISH_STOP_WORDS | EXTRA_STOP | CUE_WORDS | _area_tokens())
    vec = TfidfVectorizer(ngram_range=(1, 1), min_df=3, max_features=1500, stop_words=stop, sublinear_tf=True)
    X = vec.fit_transform(texts)
    km = KMeans(n_clusters=k, n_init=5, random_state=42).fit(X)
    terms = np.array(vec.get_feature_names_out())
    order = km.cluster_centers_.argsort(axis=1)[:, ::-1]
    labels = [", ".join(terms[order[i, :3]]) for i in range(k)]
    log("      clusters: " + " | ".join(labels))
    sil = float(silhouette_score(X, km.labels_, sample_size=min(800, X.shape[0]), random_state=0))
    save_bundle("complaint_cluster", {"vectorizer": vec, "kmeans": km, "labels": labels, "algorithm": "K-Means", "task": "clustering"})
    metrics = {"Silhouette": sil, "Inertia": float(km.inertia_), "Clusters": float(k)}
    _store("complaint_cluster", "clustering", {"K-Means": {"metrics": metrics, "seconds": time.time() - t0}}, "K-Means",
           ["tf-idf"], len(texts), 0, {}, {"labels": labels}, time.time() - t0)
    # assign clusters to the complaints already stored
    for c in Complaint.query.all():
        c.cluster_id = assign_cluster(c.text)
    db.session.commit()
    log(f"   ✔ complaint_cluster: K={k}, silhouette={sil:.3f}")


def _area_tokens() -> set:
    toks = set()
    try:
        for l in Location.query.all():
            for n in [l.name] + (l.aliases or "").split(","):
                toks.update(re.findall(r"[a-z]+", n.lower()))
    except Exception:
        pass
    return toks


# --------------------------------------------------------------------------- inference helpers
def _predict_conf(model, text):
    if hasattr(model, "predict_proba"):
        p = model.predict_proba([text])[0]
    else:
        d = model.decision_function([text])[0]
        e = np.exp((d - d.max()) * 6.0)
        p = e / e.sum()
    return int(np.argmax(p)), float(np.max(p))


def sentiment(text: str):
    t = text.lower()
    neg = sum(1 for w in NEG if w in t)
    pos = sum(1 for w in POS if w in t)
    score = max(-1.0, min(1.0, 0.3 * pos - 0.22 * neg))
    if "!" in text:
        score -= 0.05
    label = "Negative" if score < -0.15 else "Positive" if score > 0.15 else "Neutral"
    return label, round(float(score), 2)


def extract_keywords(text: str, n: int = 5):
    bundle = load_bundle("complaint_category")
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    stop = ENGLISH_STOP_WORDS | EXTRA_STOP | _area_tokens()
    try:
        vec = bundle["model"].steps[0][1]
        vocab, idf = vec.vocabulary_, vec.idf_
    except Exception:
        vocab, idf = {}, None
    scored = {}
    for tk in tokens:
        if tk in stop:
            continue
        w = idf[vocab[tk]] if idf is not None and tk in vocab else 1.0
        scored[tk] = scored.get(tk, 0) + w
    return [k for k, _ in sorted(scored.items(), key=lambda kv: -kv[1])[:n]]


def find_location(text: str):
    t = " " + re.sub(r"[^a-z0-9. ]", " ", text.lower()) + " "
    best, best_len = None, 0
    for l in Location.query.all():
        for name in [l.name.lower()] + [a.strip() for a in (l.aliases or "").split(",") if a.strip()]:
            if len(name) >= 3 and re.search(r"(?<![a-z])" + re.escape(name) + r"(?![a-z])", t) and len(name) > best_len:
                best, best_len = l, len(name)
    return best


def assign_cluster(text: str) -> int:
    b = load_bundle("complaint_cluster")
    if not b:
        return -1
    return int(b["kmeans"].predict(b["vectorizer"].transform([text]))[0])


def analyze(text: str, default_area_id=None) -> dict:
    """Full NLP analysis of one complaint. Returns plain Python types (JSON-safe)."""
    cb, pb = load_bundle("complaint_category"), load_bundle("complaint_priority")
    if not cb or not pb:
        raise RuntimeError("NLP models are not trained yet")
    ci, cconf = _predict_conf(cb["model"], text)
    pi, pconf = _predict_conf(pb["model"], text)
    category, priority = CATEGORIES[ci], PRIORITIES[pi]
    low = text.lower()
    cues = [c for c in STRONG_CUES if c in low]
    if cues and priority != "HIGH":
        priority = "HIGH"
    sent, score = sentiment(text)
    loc = find_location(text)
    if loc is None and default_area_id:
        loc = Location.query.get(default_area_id)
    return {
        "category": category, "category_confidence": round(cconf, 3),
        "priority": priority, "priority_confidence": round(pconf, 3), "priority_signals": cues[:4],
        "sentiment": sent, "sentiment_score": score,
        "keywords": extract_keywords(text),
        "location": {"id": loc.id, "name": loc.name} if loc else None,
        "cluster_id": assign_cluster(text),
    }


def cluster_labels():
    b = load_bundle("complaint_cluster")
    return b["labels"] if b else []
