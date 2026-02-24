from sqlalchemy.orm import Session

from app.repositories.driver_analytics_repo import DriverAnalyticsRepository


class DriverAnalyticsService:

    def __init__(self, db: Session):

        self.db = db
        self.repo = DriverAnalyticsRepository(db)

    def get_top_performing_drivers(
        self,
        organization_id: int,
    ):

        return self.repo.get_top_performing_drivers(
            organization_id
        )

    def get_driver_utilization(
        self,
        organization_id: int,
    ):

        return self.repo.get_driver_utilization(
            organization_id
        )

    def get_driver_performance(
        self,
        organization_id: int,
        driver_id,
    ):

        return self.repo.get_driver_performance(
            organization_id,
            driver_id,
        )