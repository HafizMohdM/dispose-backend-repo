from sqlalchemy.orm import Session

from app.models.system_setting import SystemSetting
from app.repositories.system_setting_repo import SystemSettingRepository


class SystemSettingService:

    def __init__(self, db: Session):

        self.db = db
        self.repo = SystemSettingRepository(db)

    def get_settings(
        self,
        organization_id: int | None,
    ):

        return self.repo.get_all(organization_id)

    def get_setting(
        self,
        key: str,
        organization_id: int | None,
    ):

        return self.repo.get_by_key(key, organization_id)

    def set_setting(
        self,
        key: str,
        value: str,
        organization_id: int | None,
        is_global: bool = False,
    ):

        existing = self.repo.get_by_key(key, organization_id)

        if existing:
            return self.repo.update(existing, value)

        setting = SystemSetting(
            key=key,
            value=value,
            organization_id=organization_id,
            is_global=is_global,
        )

        return self.repo.create(setting)