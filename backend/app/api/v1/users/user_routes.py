@router.get("/")
def list_users(
    current_user: User = Depends(require_permission("user.view"))
):
    return {"message": "Users list"}
