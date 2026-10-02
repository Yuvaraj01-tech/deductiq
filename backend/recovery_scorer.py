from typing import Dict, Any

class RecoveryScorer:
    """
    Predictive Recovery Scorer & Model Router:
    Calculates probability of winning the dispute, risk grade,
    and routes the claim to:
    - Tier 1: Deterministic SQL/Rules (90-95% routine cases)
    - Tier 2: Small Language Model / Statistical ML (Routine ambiguity)
    - Tier 3: Frontier LLM (Complex non-standard contracts & heavy exceptions)
    """

    @staticmethod
    def score_claim(claim: Dict[str, Any], forensic_result: Dict[str, Any]) -> Dict[str, Any]:
        amount = claim.get("amount", 0.0)
        pod_status = claim.get("pod_status", "")
        retailer = claim.get("retailer", "")
        evidence_score = forensic_result.get("evidence_score", 50)
        is_invalid = forensic_result.get("is_invalid_deduction", False)
        
        # Retailer baseline win rates from historical outcome database
        retailer_baselines = {
            "Walmart": 0.88,
            "Target": 0.84,
            "Amazon": 0.79,
            "Kroger": 0.86,
            "Costco": 0.91
        }
        base_rate = retailer_baselines.get(retailer, 0.80)
        
        # Scoring Factors
        pod_factor = 0.0
        if "Clean" in pod_status or "Stamp" in pod_status:
            pod_factor = 35.0
        elif "Exception" in pod_status:
            pod_factor = -45.0
        else:
            pod_factor = 0.0
            
        evidence_factor = (evidence_score / 100.0) * 30.0
        retailer_factor = base_rate * 25.0
        math_factor = 10.0 if not forensic_result.get("discrepancies") else -15.0
        
        raw_score = pod_factor + evidence_factor + retailer_factor + math_factor
        score = max(5.0, min(99.0, raw_score))
        
        # Route determination
        if evidence_score >= 80 and ("Clean" in pod_status or "Stamp" in pod_status) and amount < 15000:
            tier = "Rule"
            model_used = "Deterministic Forensic Rules Engine (v2.4)"
            reasoning = "Standard shortage claim with clean signed POD stamp and full documentary match. Handled 100% deterministically with 0 inference token cost."
            risk_level = "Low"
        elif amount > 25000 or "Exception" in pod_status or forensic_result.get("discrepancies"):
            tier = "Frontier"
            model_used = "Frontier Cognitive Model (Claude 3.7 / Gemini 2.0 Pro)"
            reasoning = "High dollar exposure or carrier discrepancy requires frontier multi-hop reasoning across shipping logs and contract terms."
            risk_level = "High"
        else:
            tier = "SLM"
            model_used = "Specialized CPG Deduction SLM (Fine-tuned Llama-3-8B)"
            reasoning = "Moderate ambiguity in invoice timing or promo schedule; routed to specialized domain model."
            risk_level = "Medium"
            
        expected_recovery_dollars = round((score / 100.0) * amount, 2)
        
        factors_breakdown = [
            {"factor": "Signed Carrier POD", "impact": "+35%" if pod_factor > 0 else ("-45%" if pod_factor < 0 else "0%"), "status": "Positive" if pod_factor > 0 else "Negative"},
            {"factor": "Document Packet Completeness", "impact": f"+{round(evidence_factor)}%", "status": "Positive"},
            {"factor": f"{retailer} Historical Reversal Rate", "impact": f"+{round(retailer_factor)}%", "status": "Positive"},
            {"factor": "Forensic Line Reconciliation", "impact": "+10%" if math_factor > 0 else "-15%", "status": "Positive" if math_factor > 0 else "Warning"}
        ]
        
        return {
            "win_probability": round(score, 1),
            "expected_recovery_dollars": expected_recovery_dollars,
            "routing_tier": tier,
            "model_used": model_used,
            "routing_reasoning": reasoning,
            "risk_level": risk_level,
            "factors_breakdown": factors_breakdown,
            "human_approval_required": (amount >= 10000 or score < 50.0 or risk_level == "High")
        }
