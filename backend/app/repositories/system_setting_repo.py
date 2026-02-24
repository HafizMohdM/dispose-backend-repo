from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.system_setting import SystemSetting

class SystemSettingRepository:

    def __init__(self, db: Session):
        self.db = db
    
    def get_by_key(
        self,
        key:str,
        organization_id: int | None,
        
    ) -> Optional[SystemSetting]:
        stmt=select(SystemSetting).where(
            SystemSetting.key == key,
            SystemSetting.organization_id == organization_id,
        )

        return self.db.scalar(stmt)
    
    def get_all(
        self,
        organization_id: int | None,
    ) -> List[SystemSetting]:

        stmt = select(SystemSetting).where(
            SystemSetting.organization_id == organization_id
        )

        return list(self.db.scalars(stmt).all())

    def create(
        self,
        setting: SystemSetting,
    ) -> SystemSetting:

        self.db.add(setting)
        self.db.flush()

        return setting

    def update(
        self,
        setting: SystemSetting,
        value: str,
    ) -> SystemSetting:

        setting.value = value
        self.db.flush()

        return setting