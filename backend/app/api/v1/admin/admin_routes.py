from fastapi import APIRouter, Depends
from app.core.permissions import require_permission
from app.models.user import User

router = APIRouter()

@router.get("/test-admin")
def test_admin_access(
    current_user: User = Depends(require_permission("admin.access"))
):
    return {
        "message": "Admin access granted",
        "user_id": current_user.id,
        "mobile": current_user.mobile,
    }
