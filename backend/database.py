import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "deductiq.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for fast concurrent reads and writes
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Migrations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Main deductions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deductions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        claim_number TEXT UNIQUE NOT NULL,
        retailer TEXT NOT NULL,
        deduction_code TEXT NOT NULL,
        deduction_reason TEXT NOT NULL,
        amount REAL NOT NULL,
        dispute_amount REAL NOT NULL,
        invoice_number TEXT NOT NULL,
        invoice_date TEXT NOT NULL,
        invoice_amount REAL NOT NULL,
        po_number TEXT NOT NULL,
        po_date TEXT NOT NULL,
        bol_number TEXT,
        pod_status TEXT DEFAULT 'Unverified',
        signed_qty INTEGER DEFAULT 0,
        invoiced_qty INTEGER DEFAULT 0,
        claimed_shortage_qty INTEGER DEFAULT 0,
        unit_price REAL DEFAULT 0.0,
        status TEXT DEFAULT 'New',
        win_probability REAL DEFAULT 0.0,
        risk_level TEXT DEFAULT 'Low',
        routing_tier TEXT DEFAULT 'Rule',
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Evidence graph table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evidence_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deduction_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,
        doc_reference TEXT NOT NULL,
        file_name TEXT,
        match_status TEXT DEFAULT 'Verified',
        confidence REAL DEFAULT 1.0,
        metadata_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(deduction_id) REFERENCES deductions(id) ON DELETE CASCADE
    );
    """)
    
    # Dispute dossiers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dispute_dossiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deduction_id INTEGER UNIQUE NOT NULL,
        title TEXT NOT NULL,
        legal_rebuttal TEXT NOT NULL,
        line_item_summary_json TEXT,
        citations_json TEXT,
        status TEXT DEFAULT 'Draft',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(deduction_id) REFERENCES deductions(id) ON DELETE CASCADE
    );
    """)
    
    # Portal executions & self-healing logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portal_executions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deduction_id INTEGER NOT NULL,
        retailer TEXT NOT NULL,
        portal_name TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        logs_json TEXT,
        self_healing_attempts INTEGER DEFAULT 0,
        submission_ref TEXT,
        executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(deduction_id) REFERENCES deductions(id) ON DELETE CASCADE
    );
    """)
    
    # Cash settlements & ERP credit memo verification
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cash_settlements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deduction_id INTEGER UNIQUE NOT NULL,
        remittance_advice_ref TEXT NOT NULL,
        erp_credit_memo_ref TEXT NOT NULL,
        recovered_amount REAL NOT NULL,
        success_fee REAL NOT NULL,
        settlement_date TEXT NOT NULL,
        verified_by TEXT DEFAULT 'Autonomous Cash Verifier',
        verified_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(deduction_id) REFERENCES deductions(id) ON DELETE CASCADE
    );
    """)
    
    # Audit trail
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        actor_id TEXT NOT NULL,
        actor_name TEXT NOT NULL,
        action TEXT NOT NULL,
        target_type TEXT NOT NULL,
        target_id TEXT,
        details_json TEXT
    );
    """)
    
    # System settings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Performance Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deductions_retailer ON deductions(retailer);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deductions_status ON deductions(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deductions_risk ON deductions(risk_level);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deductions_tier ON deductions(routing_tier);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_deductions_created ON deductions(created_at);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evidence_deduction ON evidence_records(deduction_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_portal_deduction ON portal_executions(deduction_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_settlement_deduction ON cash_settlements(deduction_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_logs(id DESC);")
    
    # Default settings
    default_settings = [
        ("walmart_portal_api_key", "sec_live_wm_88391740b2f", "Walmart APDP Retail Link Secure Token"),
        ("target_pol_api_key", "sec_live_tgt_991823ab47c", "Target Partners Online EDI / API Credential"),
        ("amazon_vc_api_key", "sec_live_amz_337210bc94e", "Amazon Vendor Central Dispute Key"),
        ("kroger_portal_key", "sec_live_krg_552190ee81a", "Kroger Claim Gateway Token"),
        ("costco_portal_key", "sec_live_cst_774102ff32d", "Costco Supplier Portal Key"),
        ("rule_engine_threshold", "85", "Threshold % for deterministic rule routing (Tier 1)"),
        ("slm_threshold", "60", "Threshold % for Small Language Model routing (Tier 2)"),
        ("human_approval_dollar_limit", "10000", "Disputes above this amount require human approval"),
        ("success_fee_percent", "7.5", "Performance success fee percentage on verified recovery"),
        ("erp_integration_type", "NetSuite / SAP S4HANA", "Configured ERP target connector"),
        ("edi_version", "EDI 812 Claim Dispute v4010", "Active EDI transmission standard")
    ]
    
    for k, v, desc in default_settings:
        cursor.execute("""
        INSERT OR IGNORE INTO system_settings (key, value, description)
        VALUES (?, ?, ?);
        """, (k, v, desc))
        
    # Check if migration version 1 recorded
    cursor.execute("SELECT COUNT(*) FROM schema_migrations WHERE version = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO schema_migrations (version, name) VALUES (1, 'initial_production_schema_and_indexes')")
        
    conn.commit()
    conn.close()

def log_audit(actor_id: str, actor_name: str, action: str, target_type: str, target_id: str, details: dict):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO audit_logs (actor_id, actor_name, action, target_type, target_id, details_json)
        VALUES (?, ?, ?, ?, ?, ?);
        """, (actor_id, actor_name, action, target_type, str(target_id), json.dumps(details)))
        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
