import csv
import io
import json
import random
from datetime import datetime
from database import get_connection, log_audit

class EdiErpConnector:
    """
    Connectors for EDI 812 (Credit/Debit Adjustment), EDI 856 (ASN),
    and Enterprise ERPs (NetSuite & SAP S/4HANA).
    """

    @staticmethod
    def parse_csv_claims(csv_text: str) -> list:
        reader = csv.DictReader(io.StringIO(csv_text))
        claims = []
        for row in reader:
            try:
                retailer = row.get("retailer", "Walmart").strip()
                code = row.get("deduction_code", "Code 22").strip()
                reason = row.get("deduction_reason", "Goods Shortage").strip()
                amount = float(row.get("amount", 1000.0))
                inv_num = row.get("invoice_number", f"INV-{random.randint(10000, 99999)}").strip()
                po_num = row.get("po_number", f"PO-{random.randint(10000, 99999)}").strip()
                invoiced_qty = int(row.get("invoiced_qty", 500))
                unit_price = float(row.get("unit_price", 25.0))
                claimed_shortage = int(row.get("claimed_shortage_qty", 40))
                pod_status = row.get("pod_status", "Signed Clean - Stamp Verified").strip()
                
                claims.append({
                    "retailer": retailer,
                    "deduction_code": code,
                    "deduction_reason": reason,
                    "amount": amount,
                    "dispute_amount": amount,
                    "invoice_number": inv_num,
                    "invoice_date": row.get("invoice_date", "2026-09-20"),
                    "invoice_amount": round(invoiced_qty * unit_price, 2),
                    "po_number": po_num,
                    "po_date": row.get("po_date", "2026-09-05"),
                    "bol_number": row.get("bol_number", f"BOL-{random.randint(100000, 999999)}"),
                    "pod_status": pod_status,
                    "signed_qty": invoiced_qty if "Clean" in pod_status else (invoiced_qty - claimed_shortage),
                    "invoiced_qty": invoiced_qty,
                    "claimed_shortage_qty": claimed_shortage,
                    "unit_price": unit_price,
                    "status": "New",
                    "win_probability": 94.0 if "Clean" in pod_status else 35.0,
                    "risk_level": "Low" if "Clean" in pod_status else "High",
                    "routing_tier": "Rule" if "Clean" in pod_status else "Frontier"
                })
            except Exception as e:
                continue
        return claims

    @staticmethod
    def sync_erp_connection(erp_type: str = "NetSuite") -> dict:
        """Simulate real-time health-check and bidirectional handshake with NetSuite/SAP"""
        return {
            "status": "Connected",
            "erp_type": erp_type,
            "latency_ms": 42,
            "synced_invoices_count": 1420,
            "synced_credit_memos_count": 89,
            "unresolved_deductions_flagged": 34,
            "last_sync_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
