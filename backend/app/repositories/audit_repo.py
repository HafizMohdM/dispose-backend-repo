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
                AuditLog.user_id == user_id,
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
        Filter by action prefix as a proxy for entity_type,
        since the AuditLog model does not have dedicated entity_type/entity_id columns.
        """
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.org_id == organization_id,
                AuditLog.action.ilike(f"{entity_type}%"),
            )
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
