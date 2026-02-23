from typing import Optional, Dict
from pydantic import BaseModel, Field



class UserAnalyticsResponse(BaseModel):
    total_users: int = Field(..., example=120)
    active_users: int = Field(..., example=87)


class DriverAnalyticsResponse(BaseModel):
    total_drivers: int = Field(..., example=32)
    active_drivers: int = Field(..., example=28)
    available_drivers: int = Field(..., example=14)
    busy_drivers: int = Field(..., example=8)
    offline_drivers: int = Field(..., example=6)


class PickupAnalyticsResponse(BaseModel):
    total_pickups: int = Field(..., example=840)
    completed_pickups: int = Field(..., example=790)
    cancelled_pickups: int = Field(..., example=20)
    pending_pickups: int = Field(..., example=30)
    completion_rate: float = Field(..., example=94.0)


class NotificationAnalyticsResponse(BaseModel):
    total_notifications: int = Field(..., example=1500)
    unread_notifications: int = Field(..., example=120)
    read_notifications: int = Field(..., example=1380)
    read_rate: float = Field(..., example=92.0)


class SubscriptionAnalyticsResponse(BaseModel):
    active_subscriptions: int = Field(..., example=45)
    expired_subscriptions: int = Field(..., example=5)


class UserActivityAnalyticsResponse(BaseModel):
    logins_today: int = Field(..., example=65)

class OrganizationDashboardResponse(BaseModel):
    users: UserAnalyticsResponse
    drivers: DriverAnalyticsResponse
    pickups: PickupAnalyticsResponse
    subscriptions: SubscriptionAnalyticsResponse

class SummaryDashboardResponse(BaseModel):
    users: UserAnalyticsResponse
    drivers: DriverAnalyticsResponse
    pickups: PickupAnalyticsResponse
    notifications: NotificationAnalyticsResponse
    subscriptions: SubscriptionAnalyticsResponse
    activity: UserActivityAnalyticsResponse

class TimeFilteredDashboardResponse(SummaryDashboardResponse):
    time_range_days: int

class AnalyticsSuccessResponse(BaseModel):
    success: bool = True
    data: Dict