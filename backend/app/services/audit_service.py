import json
from app.models.audit_log import AuditLog
from datetime import datetime


def log_event(db, user_id, action, org_id=None, metadata=None, session_id=None, ip_address=None):
    # Build enriched metadata for forensic audit compliance
    enriched = {}
    if metadata:
        if isinstance(metadata, dict):
            enriched.update(metadata)
        else:
            enriched["info"] = str(metadata)
    if session_id is not None:
        enriched["session_id"] = session_id
    if ip_address is not None:
        enriched["ip_address"] = ip_address

    log = AuditLog(
        user_id=user_id,
        action=action,
        org_id=org_id,
        meta=json.dumps(enriched) if enriched else None,
        created_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
