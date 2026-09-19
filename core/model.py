from __future__ import annotations
import json
from pathlib import Path
from typing import Any

SCALE_LABELS = {
    0.0: "Brak / nie można ocenić",
    1.0: "Bardzo słabo",
    2.0: "Słabo",
    3.0: "Zadowalająco",
    4.0: "Dobrze",
    5.0: "Bardzo dobrze",
}

def load_determinants(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))

def normalized_weights(determinants: list[dict[str, Any]]) -> dict[str, float]:
    total = sum(float(d["weight"]) for d in determinants)
    return {d["id"]: float(d["weight"]) / total for d in determinants}

def readiness_band(score_100: float) -> tuple[str, str]:
    if score_100 >= 85: return "Bardzo wysoki", "Projekt jest bliski gotowości, ale nadal wymaga przeglądu determinant o najniższych ocenach."
    if score_100 >= 70: return "Wysoki", "Projekt jest dobrze przygotowany, lecz wymaga ukierunkowanych poprawek przed złożeniem."
    if score_100 >= 55: return "Umiarkowany", "Projekt wymaga istotnego doskonalenia w kilku obszarach."
    if score_100 >= 40: return "Niski", "Projekt nie powinien być jeszcze składany bez głębokiej rewizji."
    return "Bardzo niski", "Projekt jest na wczesnym etapie przygotowania lub zawiera poważne luki."

def compute_results(determinants: list[dict[str, Any]], scores: dict[str, float]) -> dict[str, Any]:
    weights = normalized_weights(determinants)
    rows = []
    for det in determinants:
        vals = []
        for ind in det["indicators"]:
            val = float(scores.get(ind["id"], 0.0))
            vals.append((val, float(ind["share"])))
        denom = sum(w for _, w in vals) or 1.0
        det_score_5 = sum(v*w for v,w in vals) / denom
        det_score_100 = det_score_5 * 20.0
        contribution = det_score_100 * weights[det["id"]]
        gap = max(0.0, 100.0 - det_score_100)
        priority = gap * weights[det["id"]]
        rows.append({
            "id": det["id"], "name": det["name"], "category": det["category"],
            "weight_pct": weights[det["id"]] * 100.0, "score_5": det_score_5,
            "score_100": det_score_100, "contribution": contribution, "priority": priority,
        })
    overall = sum(r["contribution"] for r in rows)
    band, interpretation = readiness_band(overall)
    alerts = []
    for r in rows:
        if r["score_100"] < 40:
            alerts.append(f"Krytycznie niska ocena: {r['name']} ({r['score_100']:.0f}/100).")
        elif r["score_100"] < 60 and r["weight_pct"] >= 8:
            alerts.append(f"Wysokie ryzyko w ważnym obszarze: {r['name']} ({r['score_100']:.0f}/100).")
    recommendations = []
    for det in determinants:
        det_row = next(r for r in rows if r["id"] == det["id"])
        for ind in det["indicators"]:
            val = float(scores.get(ind["id"], 0.0))
            if val < 3.0:
                impact = det_row["weight_pct"] * (5.0-val)/5.0 * float(ind["share"])/100.0
                recommendations.append({"determinant":det["name"],"indicator":ind["name"],"score":val,"impact":impact,"text":ind["recommendation"]})
    recommendations.sort(key=lambda x: x["impact"], reverse=True)
    rows.sort(key=lambda x: x["priority"], reverse=True)
    return {"overall":overall,"band":band,"interpretation":interpretation,"rows":rows,"alerts":alerts,"recommendations":recommendations}
