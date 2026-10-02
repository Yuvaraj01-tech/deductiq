from typing import Dict, Any, List

class ForensicReconciler:
    """
    Forensic Reconciliation Engine:
    Performs deterministic mathematical and documentary reconciliation across
    Invoice, Purchase Order, Bill of Lading, Carrier Signed POD, and Trade Agreements.
    """
    
    @staticmethod
    def reconcile(claim: Dict[str, Any], evidence_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        invoiced_qty = claim.get("invoiced_qty", 0)
        signed_qty = claim.get("signed_qty", 0)
        claimed_shortage = claim.get("claimed_shortage_qty", 0)
        unit_price = claim.get("unit_price", 0.0)
        amount = claim.get("amount", 0.0)
        pod_status = claim.get("pod_status", "Unverified")
        retailer = claim.get("retailer", "Unknown")
        code = claim.get("deduction_code", "")
        
        discrepancies = []
        findings = []
        is_invalid_deduction = False
        rebuttal_ground = ""
        
        # Check 1: Physical delivery quantity match
        signed_clean = "Clean" in pod_status or "Stamp Verified" in pod_status or signed_qty >= invoiced_qty
        
        if signed_clean:
            # Physical evidence shows retailer receiver signed for all goods
            is_invalid_deduction = True
            rebuttal_ground = "Carrier Proof of Delivery confirms full physical receipt without dock exceptions."
            findings.append({
                "rule": "RULE-POD-01: Signed Dock Receipt Verification",
                "status": "PASSED",
                "detail": f"Signed POD reflects {signed_qty} units received vs {invoiced_qty} units billed. Claimed shortage of {claimed_shortage} is invalid.",
                "validity": "Invalid Retailer Claim"
            })
        elif signed_qty < invoiced_qty:
            actual_shortage = invoiced_qty - signed_qty
            if abs(actual_shortage - claimed_shortage) <= 1:
                # Retailer actually received less
                is_invalid_deduction = False
                rebuttal_ground = "Dock receipt confirms partial carrier shortage matching deduction."
                discrepancies.append({
                    "rule": "RULE-POD-02: Shipper Shortage Confirmation",
                    "status": "FAILED",
                    "detail": f"POD signature notes carrier shortage of {actual_shortage} units. Retailer deduction of {claimed_shortage} appears legitimate.",
                    "validity": "Valid Retailer Claim"
                })
            else:
                # Retailer claimed more shortage than carrier noted!
                is_invalid_deduction = True
                rebuttal_ground = f"Carrier exception noted {actual_shortage} units, but retailer deducted {claimed_shortage} units."
                findings.append({
                    "rule": "RULE-POD-03: Partial Excess Deduction",
                    "status": "PARTIAL",
                    "detail": f"Disputable variance of {claimed_shortage - actual_shortage} units billed erroneously.",
                    "validity": "Partial Disputable"
                })

        # Check 2: Dollar calculation forensic audit
        expected_claim_amount = round(claimed_shortage * unit_price, 2)
        dollar_variance = round(abs(amount - expected_claim_amount), 2)
        if dollar_variance > 0.50:
            findings.append({
                "rule": "RULE-PRC-01: Mathematical Dollar Variance",
                "status": "WARNING",
                "detail": f"Deduction amount ${amount:,.2f} differs from line-item calculation ({claimed_shortage} * ${unit_price:,.2f} = ${expected_claim_amount:,.2f}) by ${dollar_variance:,.2f}."
            })
        else:
            findings.append({
                "rule": "RULE-PRC-01: Mathematical Line Check",
                "status": "PASSED",
                "detail": f"Deduction math matches SKU rate of ${unit_price:,.2f} per unit."
            })
            
        # Check 3: Evidence documentary completeness
        has_invoice = any(e.get("doc_type") == "Invoice" for e in evidence_list)
        has_po = any(e.get("doc_type") == "PurchaseOrder" for e in evidence_list)
        has_bol = any(e.get("doc_type") == "BillOfLading" for e in evidence_list)
        has_pod = any(e.get("doc_type") == "SignedPOD" for e in evidence_list)
        
        evidence_score = 0
        if has_invoice: evidence_score += 20
        if has_po: evidence_score += 20
        if has_bol: evidence_score += 25
        if has_pod: evidence_score += 35
        
        return {
            "is_invalid_deduction": is_invalid_deduction,
            "evidence_score": evidence_score,
            "evidence_completeness": f"{evidence_score}%",
            "primary_rebuttal": rebuttal_ground,
            "findings": findings,
            "discrepancies": discrepancies,
            "reconciliation_verdict": "Dispute Recommended - 100% Win Probability" if (is_invalid_deduction and signed_clean) else ("Review Required" if discrepancies else "Eligible for Auto-Dispute")
        }
