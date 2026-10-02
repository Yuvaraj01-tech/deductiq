import random
from datetime import datetime, timedelta
import json
from database import get_connection, init_db

RETAILERS = [
    {"name": "Walmart", "codes": [("Code 22", "Goods Shortage / Undershipment"), ("Code 24", "Carton Shortage"), ("Code 25", "Pricing Discrepancy"), ("Code 60", "OTIF Unloading Window Fine")]},
    {"name": "Target", "codes": [("A-04", "Concealed Shortage"), ("P-12", "Base Item Price Mismatch"), ("L-01", "Late Carrier Arrival (MABD)"), ("C-19", "Barcode Label Scannability")]},
    {"name": "Amazon", "codes": [("PO-SHORT", "Vendor Central PO Receive Shortage"), ("PRICE-OVER", "Cost Price Variance Claim"), ("PREP-NC", "Prep & Polybag Non-Compliance"), ("ASIN-ERR", "Catalog ASIN Item Discrepancy")]},
    {"name": "Kroger", "codes": [("SHORT-01", "Warehouse Cross-Dock Shortage"), ("PRC-VAR", "Promotion Bracket Disallowance"), ("ADV-02", "Unauthorized Trade Allowance Deduct")]},
    {"name": "Costco", "codes": [("DEP-08", "Pallet Overhang / Dimension Penalty"), ("DED-14", "Line Item Shortage vs Manifest"), ("PRC-NET", "Off-Invoice Promo Netting Error")]}
]

def generate_seed_data(num_records=100):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check current count
    cursor.execute("SELECT COUNT(*) FROM deductions")
    if cursor.fetchone()[0] >= num_records:
        conn.close()
        print(f"Database already has {num_records} or more deductions.")
        return

    random.seed(42) # Deterministic realistic seed
    now = datetime(2026, 9, 30)
    
    status_distribution = [
        ("New", 0.18),
        ("Investigating", 0.15),
        ("ReadyToDispute", 0.20),
        ("Disputed", 0.22),
        ("Approved", 0.10),
        ("Recovered", 0.10),
        ("WrittenOff", 0.05)
    ]
    
    statuses, probs = zip(*status_distribution)
    
    print(f"Generating {num_records} CPG deduction records...")
    
    for i in range(1, num_records + 1):
        retailer_info = random.choice(RETAILERS)
        retailer_name = retailer_info["name"]
        code_tuple = random.choice(retailer_info["codes"])
        deduction_code, reason = code_tuple
        
        claim_number = f"CLM-{retailer_name[:2].upper()}-{2026}-{1000 + i}"
        invoice_number = f"INV-26-{random.randint(10000, 99999)}"
        po_number = f"PO-{retailer_name[:3].upper()}-{random.randint(20000, 89999)}"
        bol_number = f"BOL-{random.randint(100000, 999999)}"
        
        days_ago = random.randint(3, 90)
        inv_date = (now - timedelta(days=days_ago + 15)).strftime("%Y-%m-%d")
        po_date = (now - timedelta(days=days_ago + 25)).strftime("%Y-%m-%d")
        
        invoiced_qty = random.randint(100, 2500)
        unit_price = round(random.uniform(12.50, 85.00), 2)
        invoice_amount = round(invoiced_qty * unit_price, 2)
        
        # Scenario generation: Valid vs Invalid
        is_bogus_deduction = random.random() < 0.82  # 82% of retailer deductions are historically invalid/disputable
        
        if is_bogus_deduction:
            # Supplier delivered in full! Carrier signed clean POD!
            signed_qty = invoiced_qty
            claimed_shortage = random.randint(5, min(180, int(invoiced_qty * 0.25)))
            deduction_amount = round(claimed_shortage * unit_price, 2)
            pod_status = "Signed Clean - Stamp Verified"
            win_prob = round(random.uniform(84.0, 98.5), 1)
            risk = "Low"
            tier = "Rule"
        else:
            # Actual legitimate shortage or partial delivery
            claimed_shortage = random.randint(10, 100)
            signed_qty = invoiced_qty - claimed_shortage
            deduction_amount = round(claimed_shortage * unit_price, 2)
            pod_status = "Exception Noted on BOL"
            win_prob = round(random.uniform(12.0, 42.0), 1)
            risk = "High"
            tier = "Frontier"
            
        # Select status
        status = random.choices(statuses, weights=probs)[0]
        
        # If recovered, ensure high win prob
        if status == "Recovered":
            win_prob = round(random.uniform(92.0, 99.0), 1)
            risk = "Low"
        elif status == "WrittenOff":
            win_prob = round(random.uniform(5.0, 25.0), 1)
            risk = "High"
            
        cursor.execute("""
        INSERT INTO deductions (
            claim_number, retailer, deduction_code, deduction_reason, amount, dispute_amount,
            invoice_number, invoice_date, invoice_amount, po_number, po_date, bol_number,
            pod_status, signed_qty, invoiced_qty, claimed_shortage_qty, unit_price,
            status, win_probability, risk_level, routing_tier, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_number, retailer_name, deduction_code, reason, deduction_amount, deduction_amount,
            invoice_number, inv_date, invoice_amount, po_number, po_date, bol_number,
            pod_status, signed_qty, invoiced_qty, claimed_shortage, unit_price,
            status, win_prob, risk, tier,
            f"Automated reconciliation for {retailer_name} trade order. Billed {invoiced_qty} units @ ${unit_price}.",
            (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S"),
            (now - timedelta(days=max(0, days_ago - 2))).strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        deduction_id = cursor.lastrowid
        
        # Add Evidence Records to build Evidence Graph
        evidence_items = [
            ("Invoice", invoice_number, f"invoice_{invoice_number}.pdf", "Verified", 0.99, {"billed_qty": invoiced_qty, "amount": invoice_amount, "terms": "2/10 Net 30"}),
            ("PurchaseOrder", po_number, f"po_{po_number}.xml", "Verified", 0.98, {"ordered_qty": invoiced_qty, "buyer": retailer_name}),
            ("BillOfLading", bol_number, f"bol_{bol_number}.pdf", "Verified", 0.97, {"shipped_qty": invoiced_qty, "carrier": "FedEx Freight / Swift"}),
            ("SignedPOD", f"POD-{bol_number}", f"signed_pod_{bol_number}.pdf", "Verified" if pod_status.startswith("Signed Clean") else "Discrepancy", 0.96 if pod_status.startswith("Signed Clean") else 0.45, {"signed_qty": signed_qty, "stamp": pod_status}),
            ("TradeAgreement", f"AGR-{retailer_name[:3].upper()}-2026", f"contract_{retailer_name.lower()}.pdf", "Verified", 0.95, {"allowance_rate": "1.5%", "dispute_window_days": 180})
        ]
        
        for doc_type, doc_ref, fname, mstatus, conf, meta in evidence_items:
            cursor.execute("""
            INSERT INTO evidence_records (deduction_id, doc_type, doc_reference, file_name, match_status, confidence, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (deduction_id, doc_type, doc_ref, fname, mstatus, conf, json.dumps(meta)))
            
        # If Disputed or Approved or Recovered, generate a dispute dossier
        if status in ("Disputed", "Approved", "Recovered", "ReadyToDispute"):
            legal_text = (
                f"FORMAL DISPUTE NOTICE REGARDING CLAIM {claim_number}\n\n"
                f"Attention: {retailer_name} Accounts Payable & Deduction Resolution Department\n\n"
                f"Supplier hereby formally disputes the deduction of ${deduction_amount:,.2f} assessed against Invoice #{invoice_number} under Reason '{reason}' ({deduction_code}).\n\n"
                f"FORENSIC EVIDENCE SUMMARY:\n"
                f"1. Purchase Order #{po_number} required {invoiced_qty} cases.\n"
                f"2. Invoice #{invoice_number} billed {invoiced_qty} cases @ ${unit_price:,.2f} each.\n"
                f"3. Bill of Lading #{bol_number} confirms release of {invoiced_qty} units into carrier custody.\n"
                f"4. Attached Signed Proof of Delivery (POD #{bol_number}) clearly bears your receiving dock receiver signature and official receiving stamp showing '{pod_status}'.\n\n"
                f"RECONCILIATION RESULT:\n"
                f"Signed Receiving Quantity ({signed_qty}) matches Invoiced Quantity ({invoiced_qty}). The claimed shortage of {claimed_shortage} units is factually ungrounded. We request immediate credit reversal."
            )
            citations = [
                {"doc": "Signed Proof of Delivery", "page": 1, "field": "Received Quantity Stamp", "value": f"{signed_qty} Cases Verified"},
                {"doc": "Bill of Lading", "page": 1, "field": "Shipper Piece Count", "value": f"{invoiced_qty} Cases Clean"},
                {"doc": "Purchase Order", "page": 1, "field": "Contracted Line Price", "value": f"${unit_price:,.2f}"}
            ]
            line_items = [
                {"item": "SKU-99281 Premium Organic Granola 12oz", "ordered": invoiced_qty, "shipped": invoiced_qty, "received": signed_qty, "unit_price": unit_price, "variance_dollars": deduction_amount if signed_qty == invoiced_qty else 0.0}
            ]
            
            cursor.execute("""
            INSERT INTO dispute_dossiers (deduction_id, title, legal_rebuttal, line_item_summary_json, citations_json, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (deduction_id, f"Dispute Dossier - {claim_number} - {retailer_name}", legal_text, json.dumps(line_items), json.dumps(citations), "Submitted" if status in ("Disputed", "Approved", "Recovered") else "Draft"))
            
        # If Disputed or Recovered, add portal execution record
        if status in ("Disputed", "Approved", "Recovered"):
            logs = [
                {"timestamp": (now - timedelta(days=days_ago - 1)).strftime("%H:%M:%S"), "stage": "Portal Auth", "message": f"Authenticated to {retailer_name} Supplier Gateway via encrypted token."},
                {"timestamp": (now - timedelta(days=days_ago - 1)).strftime("%H:%M:%S"), "stage": "Form Navigation", "message": f"Navigated to Claim Dispute Form for Invoice {invoice_number}."},
                {"timestamp": (now - timedelta(days=days_ago - 1)).strftime("%H:%M:%S"), "stage": "Evidence Attachment", "message": f"Attached signed POD and BOL PDF evidence packets."},
                {"timestamp": (now - timedelta(days=days_ago - 1)).strftime("%H:%M:%S"), "stage": "Self-Healing Selector", "message": "Portal DOM altered selector '#submit-btn'; agent triggered semantic fallback and auto-healed target click."},
                {"timestamp": (now - timedelta(days=days_ago - 1)).strftime("%H:%M:%S"), "stage": "Confirmation", "message": f"Dispute accepted by retailer portal. Acknowledgment Ref: {retailer_name[:2].upper()}-DISP-{random.randint(500000, 999999)}."}
            ]
            cursor.execute("""
            INSERT INTO portal_executions (deduction_id, retailer, portal_name, status, logs_json, self_healing_attempts, submission_ref, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deduction_id, retailer_name, f"{retailer_name} Supplier Direct Gateway", "Success",
                json.dumps(logs), 1, f"RET-ACK-{random.randint(100000, 999999)}",
                (now - timedelta(days=days_ago - 1)).strftime("%Y-%m-%d %H:%M:%S")
            ))
            
        # If Recovered, add Cash Settlement Record
        if status == "Recovered":
            recovered_amount = deduction_amount
            success_fee = round(recovered_amount * 0.075, 2) # 7.5% fee
            settle_date = (now - timedelta(days=max(1, days_ago - 5))).strftime("%Y-%m-%d")
            cursor.execute("""
            INSERT INTO cash_settlements (deduction_id, remittance_advice_ref, erp_credit_memo_ref, recovered_amount, success_fee, settlement_date, verified_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                deduction_id, f"REMIT-ACH-{random.randint(400000, 999999)}",
                f"CM-ERP-{random.randint(700000, 899999)}",
                recovered_amount, success_fee, settle_date, "Autonomous NetSuite / SAP Bank Matcher"
            ))

    conn.commit()
    conn.close()
    print("Seed data successfully inserted!")

if __name__ == "__main__":
    generate_seed_data(100)
