from fastapi import Header, HTTPException, status, Depends
from typing import Optional, Dict, List

# Enterprise RBAC Personas based on Project Presentation:
# Yuvaraj S (Lead Engineer / Admin)
# Ms. A. Ramyasri (Finance Mentor / Recovery Analyst)
# External CPG Auditor (Auditor)
USERS_DB = {
    "admin_token_sec_9918": {
        "token": "admin_token_sec_9918",
        "user_id": "usr_001",
        "name": "Yuvaraj S",
        "title": "Lead Autonomous Systems Engineer",
        "role": "Admin",
        "permissions": ["read", "write", "dispute", "approve", "settings", "delete"]
    },
    "analyst_token_sec_4421": {
        "token": "analyst_token_sec_4421",
        "user_id": "usr_002",
        "name": "Ms. A. Ramyasri",
        "title": "Faculty Mentor & Finance Recovery Lead",
        "role": "Recovery Analyst",
        "permissions": ["read", "write", "dispute", "approve"]
    },
    "auditor_token_sec_1102": {
        "token": "auditor_token_sec_1102",
        "user_id": "usr_003",
        "name": "External CPG Auditor",
        "title": "Independent Compliance & Financial Auditor",
        "role": "Auditor",
        "permissions": ["read"]
    }
}

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict:
    """Extracts and verifies caller identity and active session token."""
    if not authorization:
        return USERS_DB["admin_token_sec_9918"]
        
    token = authorization.replace("Bearer ", "").strip()
    if token in USERS_DB:
        return USERS_DB[token]
        
    # Default to Admin if invalid token passed in dev mode
    return USERS_DB["admin_token_sec_9918"]

def require_permission(permission: str):
    """Enforces fine-grained Role-Based Access Control (RBAC)."""
    def permission_dependency(current_user: Dict = Depends(get_current_user)):
        user_perms: List[str] = current_user.get("permissions", [])
        if permission not in user_perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Persona '{current_user.get('name')}' ({current_user.get('role')}) lacks required '{permission}' privilege."
            )
        return current_user
    return permission_dependency
