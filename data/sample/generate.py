"""
Generate synthetic SOC operational data for SAT-SA development.

Produces six CSVs into data/sample/:
    entities.csv
    assets.csv
    alerts.csv
    cases.csv
    investigations.csv
    escalations.csv

Three entities are created with deliberately different behavioural profiles
so the analytics engine has interesting patterns to detect:

    BANK-A   "clean" entity, realistic closure times, proper escalations
    POWER-B  has EXECUTION GAP patterns (fast critical closures, no escalation,
             template investigations)
    TELEC-C  has NEGATIVE SPACE + ANOMALY patterns (missing categories,
             unusually low activity for its size)

Usage:
    python data/sample/generate.py
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

OUT_DIR = Path(__file__).resolve().parent
SEED = 20260927
PERIOD_START = datetime(2026, 7, 1, 0, 0, 0)
PERIOD_END = datetime(2026, 9, 30, 23, 59, 59)

random.seed(SEED)


# ----------------------------------------------------------------------------
# Entity / asset definitions
# ----------------------------------------------------------------------------
ENTITIES = [
    {
        "code": "BANK-A",
        "name": "National Banking Entity A",
        "sector": "Banking",
        "sub_sector": "Retail Banking",
        "region": "North",
        "criticality": "HIGH",
        "peer_group": "Banking-Large",
    },
    {
        "code": "POWER-B",
        "name": "Regional Power Grid Operator B",
        "sector": "Power",
        "sub_sector": "Transmission",
        "region": "West",
        "criticality": "CRITICAL",
        "peer_group": "Power-Transmission",
    },
    {
        "code": "TELEC-C",
        "name": "Telecom Service Provider C",
        "sector": "Telecom",
        "sub_sector": "Mobile Network",
        "region": "South",
        "criticality": "HIGH",
        "peer_group": "Telecom-National",
    },
]

ASSET_TYPES = ["firewall", "ids", "edr", "server", "database", "router", "gateway"]


def make_assets() -> pd.DataFrame:
    rows: list[dict] = []
    for ent in ENTITIES:
        # different fleet sizes so peer comparison is meaningful
        if ent["code"] == "BANK-A":
            n = 60
        elif ent["code"] == "POWER-B":
            n = 45
        else:
            n = 70  # telecom is largest
        for i in range(1, n + 1):
            rows.append(
                {
                    "entity_code": ent["code"],
                    "asset_code": f"{ent['code']}-AST-{i:04d}",
                    "hostname": f"{ent['code'].lower()}-{random.choice(ASSET_TYPES)}-{i:03d}",
                    "asset_type": random.choice(ASSET_TYPES),
                    "criticality": random.choice(
                        ["CRITICAL", "HIGH", "HIGH", "MEDIUM", "MEDIUM", "LOW"]
                    ),
                }
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# Alert category distributions
# ----------------------------------------------------------------------------
CATEGORIES = [
    "MALWARE",
    "PHISHING",
    "UNAUTHORIZED_ACCESS",
    "DATA_EXFILTRATION",
    "POLICY_VIOLATION",
    "DoS",
    "INSIDER_THREAT",
    "CONFIG_CHANGE",
]


def pick_category(profile: str) -> str:
    if profile == "clean":
        return random.choice(CATEGORIES)
    if profile == "execution_gap":
        # fewer DATA_EXFILTRATION and INSIDER_THREAT (they require real work)
        return random.choices(
            CATEGORIES,
            weights=[12, 14, 12, 4, 20, 6, 3, 20],
        )[0]
    if profile == "negative_space":
        # TELEC-C is missing an entire category (INSIDER_THREAT) — a blind spot
        cats = [c for c in CATEGORIES if c != "INSIDER_THREAT"]
        return random.choices(cats, weights=[12, 14, 12, 10, 20, 6, 0, 20][:len(cats)])[0]
    return random.choice(CATEGORIES)


def pick_severity(profile: str) -> str:
    if profile == "clean":
        return random.choices(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
            weights=[5, 20, 35, 30, 10],
        )[0]
    if profile == "execution_gap":
        return random.choices(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
            weights=[8, 22, 32, 28, 10],
        )[0]
    if profile == "negative_space":
        return random.choices(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"],
            weights=[3, 12, 30, 40, 15],
        )[0]
    return "MEDIUM"


def closure_minutes(profile: str, severity: str) -> int:
    if profile == "clean":
        if severity == "CRITICAL":
            return random.randint(30, 180)
        if severity == "HIGH":
            return random.randint(45, 300)
        return random.randint(60, 1440)

    if profile == "execution_gap":
        if severity == "CRITICAL":
            # planted execution gap: many critical alerts closed in under 15 minutes
            return random.choice([3, 5, 7, 9, 11, 13]) if random.random() < 0.7 else random.randint(20, 120)
        if severity == "HIGH":
            return random.randint(15, 240)
        return random.randint(60, 1440)

    if profile == "negative_space":
        # closure times normal; problem is missing categories and low overall volume
        if severity == "CRITICAL":
            return random.randint(30, 180)
        if severity == "HIGH":
            return random.randint(45, 300)
        return random.randint(60, 1440)

    return 120


def make_alerts(assets: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for ent in ENTITIES:
        profile = {
            "BANK-A": "clean",
            "POWER-B": "execution_gap",
            "TELEC-C": "negative_space",
        }[ent["code"]]

        # alert volumes vary by entity and profile
        n = {"BANK-A": 420, "POWER-B": 380, "TELEC-C": 190}[ent["code"]]
        ent_assets = assets[assets["entity_code"] == ent["code"]]

        for i in range(1, n + 1):
            detected = PERIOD_START + timedelta(
                seconds=random.randint(0, int((PERIOD_END - PERIOD_START).total_seconds()))
            )
            severity = pick_severity(profile)
            category = pick_category(profile)
            minutes = closure_minutes(profile, severity)
            closed = detected + timedelta(minutes=minutes)
            acked = detected + timedelta(minutes=random.randint(1, min(30, max(2, minutes))))

            external_id = f"{ent['code']}-ALT-{i:05d}"
            asset_code = ent_assets.sample(1).iloc[0]["asset_code"]

            rows.append(
                {
                    "entity_code": ent["code"],
                    "external_id": external_id,
                    "title": f"{category.title().replace('_', ' ')} activity detected",
                    "description": f"Automated {category} alert on asset {asset_code}",
                    "severity": severity,
                    "category": category,
                    "source_system": random.choice(["SIEM", "EDR", "NDR", "WAF"]),
                    "asset_code": asset_code,
                    "detected_at": detected.strftime("%Y-%m-%d %H:%M:%S"),
                    "acknowledged_at": acked.strftime("%Y-%m-%d %H:%M:%S"),
                    "closed_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
                    "status": random.choice(
                        ["CLOSED", "CLOSED", "CLOSED", "FALSE_POSITIVE"]
                    ),
                }
            )
    return pd.DataFrame(rows)


def make_cases(alerts: pd.DataFrame) -> pd.DataFrame:
    """Cases are opened for HIGH and CRITICAL alerts."""
    rows: list[dict] = []
    case_n = 0
    for _, a in alerts.iterrows():
        if a["severity"] not in ("CRITICAL", "HIGH"):
            continue
        # not every alert becomes a case — realistic SOC behaviour
        if random.random() > 0.55:
            continue
        case_n += 1
        opened = datetime.strptime(a["detected_at"], "%Y-%m-%d %H:%M:%S") + timedelta(
            minutes=random.randint(2, 45)
        )
        closed = datetime.strptime(a["closed_at"], "%Y-%m-%d %H:%M:%S")
        rows.append(
            {
                "entity_code": a["entity_code"],
                "external_id": f"{a['entity_code']}-CASE-{case_n:05d}",
                "alert_external_id": a["external_id"],
                "title": a["title"],
                "severity": a["severity"],
                "status": "CLOSED",
                "opened_at": opened.strftime("%Y-%m-%d %H:%M:%S"),
                "closed_at": closed.strftime("%Y-%m-%d %H:%M:%S"),
                "assigned_to": f"analyst{random.randint(1, 8):02d}",
            }
        )
    return pd.DataFrame(rows)


def make_investigations(cases: pd.DataFrame) -> pd.DataFrame:
    """
    Investigation records. For POWER-B, most CRITICAL cases get a template-like
    investigation (same content hash) — planted execution gap.
    """
    rows: list[dict] = []
    inv_n = 0
    TEMPLATE = (
        "Reviewed SIEM events, checked endpoint telemetry, confirmed alert "
        "classification. No additional indicators observed. Case closed as "
        "handled per SOP."
    )
    for _, c in cases.iterrows():
        if c["severity"] not in ("CRITICAL", "HIGH"):
            continue
        # some cases are closed without an investigation at all — realistic + a gap
        if random.random() > 0.82:
            continue

        inv_n += 1
        profile = {
            "BANK-A": "clean",
            "POWER-B": "execution_gap",
            "TELEC-C": "negative_space",
        }[c["entity_code"]]

        if profile == "execution_gap" and c["severity"] == "CRITICAL" and random.random() < 0.75:
            summary = TEMPLATE  # planted template abuse
        else:
            summary = (
                f"Investigated {c['title']}. Analyst {c['assigned_to']} reviewed "
                f"log sources, verified no lateral movement, and documented "
                f"remediation actions. Case handled per established playbook."
            )

        content_hash = hashlib.sha256(summary.encode("utf-8")).hexdigest()
        started = datetime.strptime(c["opened_at"], "%Y-%m-%d %H:%M:%S") + timedelta(
            minutes=random.randint(1, 20)
        )
        ended = datetime.strptime(c["closed_at"], "%Y-%m-%d %H:%M:%S")

        rows.append(
            {
                "entity_code": c["entity_code"],
                "case_external_id": c["external_id"],
                "investigator": c["assigned_to"],
                "started_at": started.strftime("%Y-%m-%d %H:%M:%S"),
                "ended_at": ended.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": summary,
                "evidence_notes": "" if summary == TEMPLATE else "Logs, PCAP, EDR timeline",
                "artifacts_count": 0 if summary == TEMPLATE else random.randint(1, 8),
                "content_hash": content_hash,
            }
        )
    return pd.DataFrame(rows)


def make_escalations(cases: pd.DataFrame) -> pd.DataFrame:
    """
    Escalation records for CRITICAL cases.
    POWER-B is deliberately missing most CRITICAL escalations — planted execution gap.
    """
    rows: list[dict] = []
    esc_n = 0
    for _, c in cases.iterrows():
        if c["severity"] != "CRITICAL":
            continue
        profile = {
            "BANK-A": "clean",
            "POWER-B": "execution_gap",
            "TELEC-C": "negative_space",
        }[c["entity_code"]]

        should_escalate = True
        if profile == "clean":
            should_escalate = random.random() < 0.85
        elif profile == "execution_gap":
            should_escalate = random.random() < 0.25   # most are missing
        else:
            should_escalate = random.random() < 0.55

        if not should_escalate:
            continue

        esc_n += 1
        escalated_at = datetime.strptime(c["opened_at"], "%Y-%m-%d %H:%M:%S") + timedelta(
            minutes=random.randint(5, 90)
        )
        rows.append(
            {
                "entity_code": c["entity_code"],
                "case_external_id": c["external_id"],
                "escalated_at": escalated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "escalated_to": random.choice(["SOC-Lead", "CISO-Office", "IR-Team"]),
                "level": random.choice([1, 1, 2]),
                "reason": "Critical severity alert requiring senior review",
                "acknowledged_at": (
                    escalated_at + timedelta(minutes=random.randint(5, 60))
                ).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    print(f"[generate] output dir: {OUT_DIR}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    entities_df = pd.DataFrame(ENTITIES)
    assets_df = make_assets()
    alerts_df = make_alerts(assets_df)
    cases_df = make_cases(alerts_df)
    investigations_df = make_investigations(cases_df)
    escalations_df = make_escalations(cases_df)

    entities_df.to_csv(OUT_DIR / "entities.csv", index=False)
    assets_df.to_csv(OUT_DIR / "assets.csv", index=False)
    alerts_df.to_csv(OUT_DIR / "alerts.csv", index=False)
    cases_df.to_csv(OUT_DIR / "cases.csv", index=False)
    investigations_df.to_csv(OUT_DIR / "investigations.csv", index=False)
    escalations_df.to_csv(OUT_DIR / "escalations.csv", index=False)

    print(f"[generate] entities       : {len(entities_df):>6} rows")
    print(f"[generate] assets         : {len(assets_df):>6} rows")
    print(f"[generate] alerts         : {len(alerts_df):>6} rows")
    print(f"[generate] cases          : {len(cases_df):>6} rows")
    print(f"[generate] investigations : {len(investigations_df):>6} rows")
    print(f"[generate] escalations    : {len(escalations_df):>6} rows")
    print("[generate] done")


if __name__ == "__main__":
    main()