"""
Generate a full demo dataset for all 9 CSE entities.

Produces CSVs in data/sample/full/ — one set per entity, with
different behavioural profiles so the analytics engine has variety.

Usage:
    python data/sample/generate_full.py
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent / "full"
SEED = 20260927
PERIOD_START = datetime(2026, 7, 1)
PERIOD_END = datetime(2026, 9, 30)
random.seed(SEED)


ENTITIES = [
    ("BANK-A",   "National Banking Entity A",       "Banking", "Retail Banking", "North", "HIGH",     "Banking-Large",     "clean", 420),
    ("BANK-X",   "Commercial Bank X",               "Banking", "Retail",         "East",  "HIGH",     "Banking-Large",     "clean", 280),
    ("BANK-Y",   "Cooperative Bank Y",              "Banking", "Retail",         "South", "HIGH",     "Banking-Large",     "gap",   380),
    ("POWER-B",  "Regional Power Grid Operator B",  "Power",   "Transmission",   "West",  "CRITICAL", "Power-Transmission", "gap",   380),
    ("GRID-M",   "Metro Grid Operator M",           "Power",   "Distribution",   "North", "CRITICAL", "Power-Transmission", "clean", 320),
    ("GRID-N",   "Northern Grid Operator N",        "Power",   "Transmission",   "North", "CRITICAL", "Power-Transmission", "gap",   360),
    ("TELEC-C",  "Telecom Service Provider C",      "Telecom", "Mobile Network", "South", "HIGH",     "Telecom-National",   "space", 190),
    ("TELEC-P",  "Telecom Provider P",              "Telecom", "Fixed Line",     "West",  "HIGH",     "Telecom-National",   "clean", 260),
    ("TELEC-Q",  "Telecom Provider Q",              "Telecom", "Mobile",         "East",  "HIGH",     "Telecom-National",   "gap",   240),
]

CATEGORIES = [
    "MALWARE", "PHISHING", "UNAUTHORIZED_ACCESS", "DATA_EXFILTRATION",
    "POLICY_VIOLATION", "DoS", "INSIDER_THREAT", "CONFIG_CHANGE",
]

ASSET_TYPES = ["firewall", "ids", "edr", "server", "database", "router", "gateway"]


def severity_for(profile: str) -> str:
    weights = {
        "clean": [5, 20, 35, 30, 10],
        "gap":   [8, 22, 32, 28, 10],
        "space": [3, 12, 30, 40, 15],
    }.get(profile, [5, 20, 35, 30, 10])
    return random.choices(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], weights=weights)[0]


def category_for(profile: str) -> str:
    if profile == "space":
        cats = [c for c in CATEGORIES if c != "INSIDER_THREAT"]
        return random.choice(cats)
    return random.choice(CATEGORIES)


def closure_minutes(profile: str, sev: str) -> int:
    if profile == "gap" and sev == "CRITICAL":
        return random.choice([3, 5, 7, 9, 11, 13]) if random.random() < 0.7 else random.randint(20, 120)
    if sev == "CRITICAL":
        return random.randint(30, 180)
    if sev == "HIGH":
        return random.randint(45, 300)
    return random.randint(60, 1440)


def make_entities() -> pd.DataFrame:
    return pd.DataFrame([
        {
            "code": c, "name": n, "sector": s, "sub_sector": sub,
            "region": r, "criticality": crit, "peer_group": pg,
        }
        for c, n, s, sub, r, crit, pg, _, _ in ENTITIES
    ])


def make_assets() -> pd.DataFrame:
    rows = []
    for code, *_ in ENTITIES:
        n = 30 + (abs(hash(code)) % 20)
        for i in range(1, n + 1):
            rows.append({
                "entity_code": code,
                "asset_code": f"{code}-AST-{i:04d}",
                "hostname": f"{code.lower()}-{random.choice(ASSET_TYPES)}-{i:03d}",
                "asset_type": random.choice(ASSET_TYPES),
                "criticality": random.choice(["CRITICAL", "HIGH", "HIGH", "MEDIUM", "MEDIUM", "LOW"]),
            })
    return pd.DataFrame(rows)


def make_alerts_for_entity(code, profile, count, assets):
    rows = []
    ent_assets = assets[assets["entity_code"] == code]
    for i in range(1, count + 1):
        detected = PERIOD_START + timedelta(
            seconds=random.randint(0, int((PERIOD_END - PERIOD_START).total_seconds()))
        )
        sev = severity_for(profile)
        cat = category_for(profile)
        mins = closure_minutes(profile, sev)
        closed = detected + timedelta(minutes=mins)
        acked = detected + timedelta(minutes=random.randint(1, min(30, max(2, mins))))
        asset_code = ent_assets.sample(1).iloc[0]["asset_code"]
        rows.append({
            "entity_code": code,
            "external_id": f"{code}-ALT-{i:05d}",
            "title": f"{cat.replace('_', ' ').title()} activity detected",
            "description": f"Automated {cat} alert on asset {asset_code}",
            "severity": sev,
            "category": cat,
            "source_system": random.choice(["SIEM", "EDR", "NDR", "WAF"]),
            "asset_code": asset_code,
            "detected_at": detected.strftime("%Y-%m-%d %H:%M:%S"),
            "acknowledged_at": acked.strftime("%Y-%m-%d %H:%M:%S"),
            "closed_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
            "status": random.choice(["CLOSED", "CLOSED", "CLOSED", "FALSE_POSITIVE"]),
        })
    return pd.DataFrame(rows)


def make_cases(alerts):
    rows = []
    n = 0
    for _, a in alerts.iterrows():
        if a["severity"] not in ("CRITICAL", "HIGH"):
            continue
        if random.random() > 0.55:
            continue
        n += 1
        opened = datetime.strptime(a["detected_at"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=random.randint(2, 45))
        closed = datetime.strptime(a["closed_at"], "%Y-%m-%d %H:%M:%S")
        rows.append({
            "entity_code": a["entity_code"],
            "external_id": f"{a['entity_code']}-CASE-{n:05d}",
            "alert_external_id": a["external_id"],
            "title": a["title"],
            "severity": a["severity"],
            "status": "CLOSED",
            "opened_at": opened.strftime("%Y-%m-%d %H:%M:%S"),
            "closed_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
            "assigned_to": f"analyst{random.randint(1, 8):02d}",
        })
    return pd.DataFrame(rows)


def make_investigations(cases, profiles):
    TEMPLATE = (
        "Reviewed SIEM events, checked endpoint telemetry, confirmed alert "
        "classification. No additional indicators observed. Case closed as "
        "handled per SOP."
    )
    rows = []
    n = 0
    for _, c in cases.iterrows():
        if random.random() > 0.82:
            continue
        n += 1
        profile = profiles[c["entity_code"]]
        if profile == "gap" and c["severity"] == "CRITICAL" and random.random() < 0.75:
            summary = TEMPLATE
        else:
            summary = (
                f"Investigated {c['title']}. Analyst {c['assigned_to']} reviewed "
                f"log sources, verified no lateral movement, and documented "
                f"remediation actions."
            )
        ch = hashlib.sha256(summary.encode()).hexdigest()
        started = datetime.strptime(c["opened_at"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=random.randint(1, 20))
        ended = datetime.strptime(c["closed_at"], "%Y-%m-%d %H:%M:%S")
        rows.append({
            "entity_code": c["entity_code"],
            "case_external_id": c["external_id"],
            "investigator": c["assigned_to"],
            "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
            "ended_at": ended.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "evidence_notes": "" if summary == TEMPLATE else "Logs, PCAP, EDR timeline",
            "artifacts_count": 0 if summary == TEMPLATE else random.randint(1, 8),
            "content_hash": ch,
        })
    return pd.DataFrame(rows)


def make_escalations(cases, profiles):
    rows = []
    n = 0
    for _, c in cases.iterrows():
        if c["severity"] != "CRITICAL":
            continue
        profile = profiles[c["entity_code"]]
        rate = {"clean": 0.85, "gap": 0.25, "space": 0.55}.get(profile, 0.6)
        if random.random() > rate:
            continue
        n += 1
        esc_at = datetime.strptime(c["opened_at"], "%Y-%m-%d %H:%M:%S") + timedelta(minutes=random.randint(5, 90))
        ack = esc_at + timedelta(minutes=random.randint(5, 60))
        rows.append({
            "entity_code": c["entity_code"],
            "case_external_id": c["external_id"],
            "escalated_at": esc_at.strftime("%Y-%m-%d %H:%M:%S"),
            "escalated_to": random.choice(["SOC-Lead", "CISO-Office", "IR-Team"]),
            "level": random.choice([1, 1, 2]),
            "reason": "Critical severity alert requiring senior review",
            "acknowledged_at": ack.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return pd.DataFrame(rows)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[generate_full] output: {OUT_DIR}")

    profiles = {c: p for c, *_rest, p, _n in ENTITIES}

    entities = make_entities()
    entities.to_csv(OUT_DIR / "entities.csv", index=False)
    print(f"  entities: {len(entities)} rows")

    assets = make_assets()
    assets.to_csv(OUT_DIR / "assets.csv", index=False)
    print(f"  assets: {len(assets)} rows")

    all_alerts = []
    for code, name, sector, sub, region, crit, pg, profile, count in ENTITIES:
        df = make_alerts_for_entity(code, profile, count, assets)
        df.to_csv(OUT_DIR / f"alerts_{code}.csv", index=False)
        all_alerts.append(df)
        print(f"  alerts_{code}: {len(df)} rows")
    alerts_all = pd.concat(all_alerts, ignore_index=True)

    cases_all = make_cases(alerts_all)
    for code, *_ in ENTITIES:
        sub = cases_all[cases_all["entity_code"] == code]
        if not sub.empty:
            sub.to_csv(OUT_DIR / f"cases_{code}.csv", index=False)
    print(f"  cases: {len(cases_all)} rows")

    inv_all = make_investigations(cases_all, profiles)
    for code, *_ in ENTITIES:
        sub = inv_all[inv_all["entity_code"] == code]
        if not sub.empty:
            sub.to_csv(OUT_DIR / f"investigations_{code}.csv", index=False)
    print(f"  investigations: {len(inv_all)} rows")

    esc_all = make_escalations(cases_all, profiles)
    for code, *_ in ENTITIES:
        sub = esc_all[esc_all["entity_code"] == code]
        if not sub.empty:
            sub.to_csv(OUT_DIR / f"escalations_{code}.csv", index=False)
    print(f"  escalations: {len(esc_all)} rows")

    print("[generate_full] done")


if __name__ == "__main__":
    main()