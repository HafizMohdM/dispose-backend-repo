from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_audit_logs(self, organization_id: int, skip: int = 0, limit: int = 50):
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.org_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_audit_log_by_id(self, audit_log_id: int, organization_id: int):
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.id == audit_log_id,
                AuditLog.org_id == organization_id,
            )
            .first()
        )

    def get_user_audit_logs(
        self, organization_id: int, user_id: int, skip: int = 0, limit: int = 50
    ):
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.org_id == organization_id,
                AuditLog.changed_by == user_id,
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_entity_audit_logs(
        self,
        organization_id: int,
        entity_type: str,
        entity_id: int,
        skip: int = 0,
        limit: int = 50,
    ):
        """
        Filter by native entity_type and entity_id fields.
        """
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.org_id == organization_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
