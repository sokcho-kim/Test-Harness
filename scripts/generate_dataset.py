"""RegScan V4 briefings → promptfoo 테스트 데이터셋 생성

reconstruct_drug_data() 로직을 재활용하여 다양한 약물 유형의 테스트 케이스를 생성.

Usage:
    python scripts/generate_dataset.py
"""

import json
import sys
from pathlib import Path

REGSCAN_DIR = Path(r"C:\Jimin\RegScan")
HARNESS_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = HARNESS_DIR / "evals" / "regscan" / "datasets" / "drug_samples.json"
SNAPSHOT_DIR = REGSCAN_DIR / "output" / "briefings" / "snapshots" / "2026-02-25_v4"
MAIN_DIR = REGSCAN_DIR / "output" / "briefings"


def _compute_status_text(approved, date_str, brand=""):
    if approved:
        label = f"승인 완료 ({date_str})" if date_str else "승인 완료"
        if brand:
            label += f" ({brand})"
        return label
    return "미허가 (not_approved)"


def _compute_copay_text(source_data):
    hira_status = source_data.get("hira_status", "")
    hira_price = source_data.get("hira_price")
    if hira_status == "reimbursed" and hira_price:
        copay = hira_price * 0.3
        return f"HIRA 등재 약제 (상한가 \u20a9{hira_price:,.0f}). 일반 급여 시 본인부담 약 \u20a9{copay:,.0f} (30%)."
    if not source_data.get("mfds_approved", False):
        return "국내 미허가 \u2014 급여 적용 불가. 전액 환자 부담."
    return "국내 허가 완료, 급여 미등재. 비급여 처방 시 전액 환자 부담."


def reconstruct_drug_data(article_json):
    sd = article_json.get("source_data", {})
    v4f = article_json.get("_v4_facts", {})
    known_inns = article_json.get("_known_inns", [])
    inn = article_json.get("inn", sd.get("inn", ""))

    drug_data = {
        "inn": inn,
        "fda": {
            "approved": sd.get("fda_approved", False),
            "date": sd.get("fda_date"),
        },
        "ema": {
            "approved": sd.get("ema_approved", False),
            "date": sd.get("ema_date"),
        },
        "mfds": {
            "approved": sd.get("mfds_approved", False),
            "date": sd.get("mfds_date"),
            "brand_name": sd.get("mfds_brand_name", ""),
        },
        "hira": {
            "status": sd.get("hira_status"),
            "price": sd.get("hira_price"),
            "criteria": sd.get("hira_criteria", ""),
        },
        "cris": {
            "trial_count": sd.get("cris_trial_count", 0),
            "trials": [],
        },
        "analysis": {
            "domestic_status": sd.get("domestic_status", "unknown"),
            "global_score": sd.get("global_score", 0),
            "hot_issue_reasons": sd.get("analysis", {}).get("hot_issue_reasons", []),
        },
        "context": {
            "therapeutic_areas": sd.get("therapeutic_areas", []),
        },
        "d_day_text": v4f.get("d_day_text", ""),
        "fda_status_text": _compute_status_text(
            sd.get("fda_approved", False), sd.get("fda_date")
        ),
        "ema_status_text": _compute_status_text(
            sd.get("ema_approved", False), sd.get("ema_date")
        ),
        "mfds_status_text": _compute_status_text(
            sd.get("mfds_approved", False),
            sd.get("mfds_date"),
            sd.get("mfds_brand_name", ""),
        ),
        "copay_scenario_text": _compute_copay_text(sd),
        "valid_competitors": [
            {"inn": c}
            for c in known_inns
            if c.upper() != inn.upper()
        ],
        "approval_summary_table": v4f.get("approval_summary_table", ""),
        "cost_scenario_table": v4f.get("cost_scenario_table", ""),
    }
    if v4f.get("price_spectrum"):
        drug_data["price_spectrum"] = v4f["price_spectrum"]
    return drug_data


def find_file(fname):
    for d in [SNAPSHOT_DIR, MAIN_DIR]:
        fpath = d / fname
        if fpath.exists():
            return fpath
        # case-insensitive fallback
        for f in d.iterdir():
            if f.name.lower() == fname.lower() and f.suffix == ".json":
                return f
    return None


TARGETS = [
    # (파일명, 카테고리 설명)
    ("ZANIDATAMAB-HRII.json", "oncology, 미허가, FDA+EMA, high score"),
    ("polatuzumab_vedotin.json", "oncology, 미허가, 장기 지연(6년)"),
    ("ZOLBETUXIMAB.json", "oncology, 미허가, uncertain"),
    ("IVOSIDENIB.json", "oncology, 미허가, uncertain"),
    ("entrectinib.json", "oncology, reimbursed, 미허가+급여 edge case"),
    ("blinatumomab.json", "oncology, reimbursed, 초고가"),
    ("daratumumab.json", "oncology, reimbursed, 고가"),
    ("lenvatinib.json", "oncology+metabolic, reimbursed"),
    ("semaglutide.json", "metabolic, reimbursed"),
    ("cabozantinib.json", "oncology+metabolic, reimbursed, 다적응증"),
    ("ECULIZUMAB-AAGH.json", "rare_disease, 미허가"),
    ("MIGALASTAT_HYDROCHLORIDE.json", "rare_disease, 미허가"),
    ("Sotatercept-csrk.json", "cardiovascular, 미허가"),
    ("DULAGLUTIDE.json", "metabolic, 미허가"),
    ("SPESOLIMAB-SBZO.json", "immunology, 미허가"),
]


def main():
    dataset = []
    for fname, category in TARGETS:
        fpath = find_file(fname)
        if not fpath:
            print(f"  SKIP: {fname} (not found)")
            continue

        article = json.loads(fpath.read_text(encoding="utf-8"))
        drug_data = reconstruct_drug_data(article)
        drug_data_str = json.dumps(drug_data, ensure_ascii=False, indent=2)

        dataset.append({
            "description": f"{article.get('inn', fname)} ({category})",
            "vars": {
                "drug_data": drug_data_str,
            },
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\nGenerated {len(dataset)} test cases -> {OUTPUT_FILE}")
    for i, tc in enumerate(dataset):
        d = json.loads(tc["vars"]["drug_data"])
        desc = tc["description"]
        print(f"  [{i + 1:2d}] {d['inn']:40s} | {desc.split('(', 1)[1].rstrip(')')}")


if __name__ == "__main__":
    main()
