"""Seed the database with synthetic customer data from JSON files."""

import json
from pathlib import Path
from src.database.schema import init_database
from src.database import crud


def seed_from_case_file(conn, case_path: str) -> tuple[str, str]:
    """Load a case JSON file and seed the database. Returns (customer_id, review_id)."""
    with open(case_path) as f:
        case = json.load(f)

    customer_data = case["customer"]
    if customer_data["type"] == "corporate":
        customer_data["full_name"] = customer_data.get("company_name", customer_data.get("full_name", "Unknown"))

    customer_id = crud.create_customer(conn, customer_data)
    review_id = crud.create_review(conn, case["case_id"], customer_id, case.get("submitted_at"))

    for doc in case.get("identification_documents", []):
        doc_record = {
            "type": doc.get("type", "unknown"),
            "category": doc.get("category"),
            "document_number": doc.get("document_number"),
            "issuing_country": doc.get("issuing_country"),
            "issue_date": doc.get("issue_date"),
            "expiry_date": doc.get("expiry_date"),
            "verified": doc.get("verified", False),
            "verification_notes": doc.get("note"),
        }
        crud.add_document(conn, review_id, doc_record)

    screening_flags = case.get("screening_flags", {})
    result_map = {"findings": "potential_match", "clear": "clear"}
    for stype, sdata in screening_flags.items():
        screening_type = stype.replace("_screening", "")
        raw_result = sdata.get("result", "clear")
        normalized_result = result_map.get(raw_result, raw_result)
        crud.add_screening_result(conn, review_id, {
            "screening_type": screening_type,
            "result": normalized_result,
            "matched_list": sdata.get("matched_list"),
            "match_confidence": float(sdata["match_confidence"]) / 100.0 if "match_confidence" in sdata else None,
            "match_details": sdata.get("details"),
        })

    crud.add_audit_log(conn, review_id, "intake", "case_loaded",
                       f"Case {case['case_id']} loaded from {Path(case_path).name}")

    return customer_id, review_id


def seed_all(db_path: str = "data/compliance.db") -> dict:
    """Seed database with all case files. Returns mapping of case_id to (customer_id, review_id)."""
    conn = init_database(db_path)
    results = {}

    data_dir = Path("data/customers")
    for case_file in sorted(data_dir.glob("*.json")):
        customer_id, review_id = seed_from_case_file(conn, str(case_file))
        with open(case_file) as f:
            case_id = json.load(f)["case_id"]
        results[case_id] = {"customer_id": customer_id, "review_id": review_id}
        print(f"Seeded: {case_id} -> customer={customer_id}, review={review_id}")

    conn.close()
    return results


if __name__ == "__main__":
    seed_all()
