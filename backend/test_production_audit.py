import os
import requests
import json
import sys
import io

BASE_URL = "http://127.0.0.1:8000"

ADMIN_HEADER = {"Authorization": "Bearer admin_token_sec_9918"}
ANALYST_HEADER = {"Authorization": "Bearer analyst_token_sec_4421"}
AUDITOR_HEADER = {"Authorization": "Bearer auditor_token_sec_1102"}

def run_tests():
    passed = 0
    failed = 0

    def assert_test(condition, name):
        nonlocal passed, failed
        if condition:
            print(f"[PASS] {name}")
            passed += 1
        else:
            print(f"[FAIL] {name}")
            failed += 1

    print("\n--- 1. APPLICATION & BACKEND STARTUP ---")
    res = requests.get(f"{BASE_URL}/api/health")
    assert_test(res.status_code == 200 and res.json().get("status") == "healthy", "Health check endpoint returns healthy")

    res = requests.get(f"{BASE_URL}/")
    assert_test(res.status_code == 200 and "DeductIQ" in res.text, "Root / serves index.html with DeductIQ content")

    print("\n--- 2. FRONTEND COMPILATION & STATIC ASSETS ---")
    res_css = requests.get(f"{BASE_URL}/static/css/style.css")
    assert_test(res_css.status_code == 200 and len(res_css.text) > 500, "CSS style sheet served successfully")

    res_js = requests.get(f"{BASE_URL}/static/js/app.js")
    assert_test(res_js.status_code == 200 and "DeductIQ" in res_js.text, "JavaScript app controller served successfully")

    print("\n--- 3. DATABASE & MIGRATIONS ---")
    import sqlite3
    db_file = os.path.join(os.path.dirname(__file__), "deductiq.db")
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT version FROM schema_migrations")
    migrations = cur.fetchall()
    assert_test(len(migrations) >= 1 and migrations[0][0] == 1, "Database migrations table applied version 1")
    conn.close()

    print("\n--- 4. AUTHENTICATION & USER PERSONAS ---")
    res = requests.get(f"{BASE_URL}/api/auth/me", headers=ADMIN_HEADER)
    assert_test(res.status_code == 200 and res.json().get("role") == "Admin", "Admin authentication verified")

    res = requests.get(f"{BASE_URL}/api/auth/me", headers=ANALYST_HEADER)
    assert_test(res.status_code == 200 and res.json().get("role") == "Recovery Analyst", "Analyst authentication verified")

    res = requests.get(f"{BASE_URL}/api/auth/me", headers=AUDITOR_HEADER)
    assert_test(res.status_code == 200 and res.json().get("role") == "Auditor", "Auditor authentication verified")

    print("\n--- 5. AUTHORIZATION & RBAC ENFORCEMENT ---")
    # Auditor cannot update settings (requires 'settings')
    res = requests.put(f"{BASE_URL}/api/settings", json={"settings": {"rule_engine_threshold": "90"}}, headers=AUDITOR_HEADER)
    assert_test(res.status_code == 403, "Auditor blocked with 403 Forbidden from updating settings")

    # Admin can update settings
    res = requests.put(f"{BASE_URL}/api/settings", json={"settings": {"rule_engine_threshold": "85"}}, headers=ADMIN_HEADER)
    assert_test(res.status_code == 200 and res.json().get("success") is True, "Admin authorized to update settings")

    print("\n--- 6. DASHBOARD CALCULATIONS & METRICS ---")
    res = requests.get(f"{BASE_URL}/api/dashboard/metrics")
    assert_test(res.status_code == 200, "Dashboard metrics endpoint returns 200")
    data = res.json()
    assert_test(data.get("total_claims", 0) > 0, f"Total claims count > 0 (found {data.get('total_claims')})")
    assert_test(data.get("total_deductions_amount", 0) > 0, f"Total deductions amount > 0 (found ${data.get('total_deductions_amount'):,.2f})")
    assert_test(len(data.get("retailer_breakdown", [])) >= 5, "Retailer breakdown includes Walmart, Target, Amazon, Kroger, Costco")
    assert_test("roi_multiplier" in data and "x" in data["roi_multiplier"], f"ROI multiplier calculated ({data['roi_multiplier']})")

    print("\n--- 7. CRUD OPERATIONS ON CLAIMS ---")
    # CREATE
    new_claim = {
        "retailer": "Walmart",
        "deduction_code": "Code 22",
        "deduction_reason": "Goods Shortage / Undershipment",
        "amount": 5420.00,
        "invoice_number": "INV-AUDIT-001",
        "invoice_date": "2026-09-10",
        "invoice_amount": 30000.00,
        "po_number": "PO-WM-99001",
        "po_date": "2026-09-01",
        "bol_number": "BOL-99001",
        "pod_status": "Signed Clean - Stamp Verified",
        "signed_qty": 1000,
        "invoiced_qty": 1000,
        "claimed_shortage_qty": 100,
        "unit_price": 54.20
    }
    # Auditor cannot create (requires 'write')
    res = requests.post(f"{BASE_URL}/api/claims", json=new_claim, headers=AUDITOR_HEADER)
    assert_test(res.status_code == 403, "Auditor blocked with 403 from creating claim")

    # Admin creates claim
    res = requests.post(f"{BASE_URL}/api/claims", json=new_claim, headers=ADMIN_HEADER)
    assert_test(res.status_code == 201 and res.json().get("success") is True, "Admin successfully created claim")
    created_id = res.json().get("claim_id")

    # READ
    res = requests.get(f"{BASE_URL}/api/claims/{created_id}")
    assert_test(res.status_code == 200, "Successfully fetched created claim")
    detail = res.json()
    assert_test(len(detail.get("evidence_graph", [])) >= 4, f"Evidence graph auto-bound {len(detail.get('evidence_graph', []))} documentary nodes")

    # UPDATE
    res = requests.put(f"{BASE_URL}/api/claims/{created_id}", json={"notes": "Updated by Automated Audit Suite"}, headers=ADMIN_HEADER)
    assert_test(res.status_code == 200 and res.json().get("success") is True, "Successfully updated claim")

    print("\n--- 8. AI FUNCTIONALITY: FORENSIC RECONCILIATION & SCORING ---")
    # Reconcile
    res = requests.post(f"{BASE_URL}/api/claims/{created_id}/reconcile")
    assert_test(res.status_code == 200, "Forensic reconciliation completed")
    f_res = res.json().get("reconciliation", {})
    assert_test(f_res.get("is_invalid_deduction") is True, "Forensic engine correctly identified clean POD as invalid retailer deduction")
    assert_test(f_res.get("evidence_score") == 100, "Forensic completeness reached 100%")

    # Score
    res = requests.post(f"{BASE_URL}/api/claims/{created_id}/score")
    assert_test(res.status_code == 200, "Predictive recovery scorer completed")
    s_res = res.json().get("scoring", {})
    assert_test(s_res.get("win_probability") >= 90.0, f"Win probability score high ({s_res.get('win_probability')}%)")
    assert_test(s_res.get("routing_tier") == "Rule", "Claim correctly routed to Tier 1 Zero-Cost Rule Engine")

    # Dossier Generation
    res = requests.post(f"{BASE_URL}/api/claims/{created_id}/generate-dossier", headers=ADMIN_HEADER)
    assert_test(res.status_code == 200, "Dispute dossier generated successfully")
    dossier = res.json().get("dossier", {})
    assert_test("UCC" in dossier.get("legal_rebuttal", "") or "Dispute" in dossier.get("legal_rebuttal", ""), "Dossier includes formal legal rebuttal")

    print("\n--- 9. AUTONOMOUS 6-STAGE OUTCOME LOOP & SELF-HEALING PORTAL ---")
    res = requests.post(f"{BASE_URL}/api/claims/{created_id}/autonomous-loop", headers=ADMIN_HEADER)
    assert_test(res.status_code == 200 and res.json().get("success") is True, "Autonomous recovery loop ran successfully")
    loop_res = res.json()
    portal_res = loop_res.get("portal", {})
    assert_test("acknowledgment_code" in portal_res, f"Retailer portal issued acknowledgment: {portal_res.get('acknowledgment_code')}")
    assert_test(portal_res.get("self_healing_attempts") == 1, "Self-healing DOM mutation fallback executed")

    print("\n--- 10. CASH RECOVERY & ERP SETTLEMENT VERIFICATION ---")
    res = requests.post(f"{BASE_URL}/api/claims/{created_id}/verify-recovery", headers=ADMIN_HEADER)
    assert_test(res.status_code == 200 and res.json().get("success") is True, "Cash recovery verified against ERP credit memo")
    settle = res.json()
    assert_test(settle.get("recovered_amount") == 5420.00, f"Recovered amount matches ${settle.get('recovered_amount')}")
    assert_test(settle.get("success_fee") == round(5420.00 * 0.075, 2), f"7.5% success fee calculated correctly (${settle.get('success_fee')})")

    print("\n--- 11. DELETE OPERATION ---")
    # Auditor cannot delete (requires 'delete')
    res = requests.delete(f"{BASE_URL}/api/claims/{created_id}", headers=AUDITOR_HEADER)
    assert_test(res.status_code == 403, "Auditor blocked with 403 from deleting claim")

    # Admin deletes claim
    res = requests.delete(f"{BASE_URL}/api/claims/{created_id}", headers=ADMIN_HEADER)
    assert_test(res.status_code == 200 and res.json().get("success") is True, "Admin successfully deleted claim")

    # Verify deletion
    res = requests.get(f"{BASE_URL}/api/claims/{created_id}")
    assert_test(res.status_code == 404, "Claim 404 confirmed after deletion")

    print("\n--- 12. SEARCH, FILTER, SORT & PAGINATION ---")
    # Search
    res = requests.get(f"{BASE_URL}/api/claims?search=Walmart")
    assert_test(res.status_code == 200 and res.json().get("total_records") > 0, "Search query filter returns results")

    # Retailer filter
    res = requests.get(f"{BASE_URL}/api/claims?retailer=Target")
    assert_test(res.status_code == 200 and all(r["retailer"] == "Target" for r in res.json().get("records", [])), "Retailer filter strictly matches Target")

    # Pagination
    res1 = requests.get(f"{BASE_URL}/api/claims?page=1&limit=5")
    res2 = requests.get(f"{BASE_URL}/api/claims?page=2&limit=5")
    assert_test(len(res1.json().get("records", [])) == 5 and len(res2.json().get("records", [])) == 5, "Pagination limit=5 returns 5 rows per page")
    assert_test(res1.json().get("records")[0]["id"] != res2.json().get("records")[0]["id"], "Page 1 and Page 2 contain distinct records")

    # Sorting
    res_sort = requests.get(f"{BASE_URL}/api/claims?sort_by=amount&sort_dir=desc&limit=5")
    amounts = [r["amount"] for r in res_sort.json().get("records", [])]
    assert_test(amounts == sorted(amounts, reverse=True), "Sorting by amount desc strictly verified")

    print("\n--- 13. FILE EXPORTS & TEMPLATES ---")
    # Template
    res = requests.get(f"{BASE_URL}/api/claims/template")
    assert_test(res.status_code == 200 and "retailer,deduction_code" in res.text, "CSV template download endpoint returns CSV format")

    # Export CSV
    res = requests.get(f"{BASE_URL}/api/claims-export")
    assert_test(res.status_code == 200 and "claim_number" in res.text, "Claims CSV export endpoint returns valid CSV")

    print("\n--- 14. FILE UPLOADS ---")
    sample_csv = (
        "retailer,deduction_code,deduction_reason,amount,invoice_number,invoice_date,invoiced_qty,unit_price,claimed_shortage_qty,po_number,po_date,bol_number,pod_status\n"
        "Walmart,Code 22,Goods Shortage / Undershipment,4250.00,INV-IMPORT-991,2026-09-12,1200,50.00,85,PO-WM-991,2026-09-01,BOL-882910,Signed Clean - Stamp Verified\n"
    )
    files = {"file": ("test_import.csv", io.BytesIO(sample_csv.encode("utf-8")), "text/csv")}
    res = requests.post(f"{BASE_URL}/api/claims/upload", files=files, headers=ADMIN_HEADER)
    assert_test(res.status_code == 200 and res.json().get("records_imported") == 1, "CSV upload parsed and inserted claim into DB")

    print("\n--- 15. EXTERNAL INTEGRATION CONNECTORS ---")
    for target in ["Walmart", "Target", "Amazon", "Kroger", "Costco", "ERP"]:
        res = requests.post(f"{BASE_URL}/api/settings/test-connection", json={"target": target})
        assert_test(res.status_code == 200 and res.json().get("status") in ("Healthy", "Connected"), f"Integration gateway for {target} responsive")

    print("\n--- 16. SYSTEM AUDIT LOGGING ---")
    res = requests.get(f"{BASE_URL}/api/audit-logs?limit=10")
    assert_test(res.status_code == 200 and len(res.json()) > 0, "Audit logs recorded actions and returned entries")

    print("\n--- 17. ERROR HANDLING & EDGE CASES ---")
    # Non-existent claim
    res = requests.get(f"{BASE_URL}/api/claims/99999999")
    assert_test(res.status_code == 404, "Non-existent claim gracefully returns 404 Not Found")

    # Invalid payload
    res = requests.post(f"{BASE_URL}/api/claims", json={"bad_field": 123}, headers=ADMIN_HEADER)
    assert_test(res.status_code == 422, "Malformed payload gracefully returns 422 Unprocessable Entity")

    print("\n=======================================================")
    print(f"AUDIT SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=======================================================")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
