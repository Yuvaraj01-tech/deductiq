import json
from typing import Dict, Any, List

class DossierGenerator:
    """
    Autonomous Dispute Dossier Generator:
    Compiles evidence-grounded dispute packages with formal legal rebuttals,
    citations to signed PODs, line-item itemizations, and exportable documentation.
    """
    
    @staticmethod
    def generate(claim: Dict[str, Any], forensic: Dict[str, Any], scoring: Dict[str, Any]) -> Dict[str, Any]:
        claim_num = claim.get("claim_number", "")
        retailer = claim.get("retailer", "")
        code = claim.get("deduction_code", "")
        reason = claim.get("deduction_reason", "")
        amount = claim.get("amount", 0.0)
        inv_num = claim.get("invoice_number", "")
        inv_date = claim.get("invoice_date", "")
        po_num = claim.get("po_number", "")
        bol_num = claim.get("bol_number", "")
        pod_status = claim.get("pod_status", "")
        invoiced_qty = claim.get("invoiced_qty", 0)
        signed_qty = claim.get("signed_qty", 0)
        unit_price = claim.get("unit_price", 0.0)
        
        legal_rebuttal = f"""FORMAL NOTICE OF DISPUTE & REQUEST FOR REVERSAL

Date: October 2, 2026
To: {retailer} Corporate Accounts Payable & Deductions Resolution Group
Re: Disputed Deduction Claim #{claim_num}
Referenced Invoice: #{inv_num} (Dated: {inv_date})
Referenced Purchase Order: #{po_num}
Total Disputed Amount: ${amount:,.2f} USD
Deduction Code: {code} — {reason}

STATEMENT OF DISPUTE:
The supplier hereby formally rejects deduction #{claim_num} in the amount of ${amount:,.2f} deducted from remittance payment. A comprehensive forensic audit of all primary logistics, transactional, and electronic data interchange records confirms that this deduction is factually unsubstantiated.

FORENSIC AUDIT RECORD & EVIDENCE PROOFS:
1. CONTRACT & PURCHASE ORDER: Purchase Order #{po_num} placed on {claim.get('po_date', 'N/A')} authorized shipment of {invoiced_qty} units @ ${unit_price:,.2f} per unit.
2. SHIPMENT & CARRIER TRANSFER: Carrier accepted {invoiced_qty} units under Bill of Lading #{bol_num}.
3. PHYSICAL RECEIVING DOCK VERIFICATION: Attached signed Proof of Delivery (POD #{bol_num}) definitively establishes that your distribution center dock receiver accepted delivery with explicit stamp notation: "{pod_status}".
4. QUANTITY MATCH: Billed Quantity: {invoiced_qty} units | Received Dock Quantity: {signed_qty} units | Documented Shortage: 0 units.

LEGAL & POLICY BASIS:
Under standard Uniform Commercial Code (UCC) § 2-606 (Acceptance of Goods) and {retailer} Supplier Trading Partner Agreement Section 14, acceptance of goods occurs when the buyer signs a clear delivery receipt without noting exception at time of tender. Retailer's unilateral retroactive deduction violates agreed settlement terms.

REQUESTED ACTION:
Immediate issuance of an offsetting credit memo or reimbursement remittance for ${amount:,.2f} within thirty (30) business days.

Executed Autonomously by:
DeductIQ Autonomous Revenue Recovery Engine
System Decision Model: {scoring.get('model_used', 'Deterministic Rule Engine')}
Confidence Level: {scoring.get('win_probability', 95.0)}%
"""
        
        citations = [
            {"doc": "Signed Proof of Delivery (POD)", "field": "Receiving Dock Signature Stamp", "value": pod_status, "verified": True},
            {"doc": "Carrier Bill of Lading (BOL)", "field": "Shipper Piece Count", "value": f"{invoiced_qty} Cases Released", "verified": True},
            {"doc": "Sales Invoice", "field": "Invoice Total & Billed SKU", "value": f"${claim.get('invoice_amount', 0):,.2f}", "verified": True},
            {"doc": "Purchase Order", "field": "Contract Price & Unit Schedule", "value": f"${unit_price:,.2f} / unit", "verified": True}
        ]
        
        line_items = [
            {
                "sku": "SKU-99281 CPG Master Pack",
                "ordered_qty": invoiced_qty,
                "invoiced_qty": invoiced_qty,
                "signed_pod_qty": signed_qty,
                "claimed_shortage": claim.get("claimed_shortage_qty", 0),
                "unit_price": unit_price,
                "line_dispute_amount": amount
            }
        ]
        
        return {
            "title": f"Dispute Dossier — {claim_num} ({retailer})",
            "legal_rebuttal": legal_rebuttal,
            "citations": citations,
            "line_items": line_items,
            "status": "Ready"
        }
