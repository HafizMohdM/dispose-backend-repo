@router.post("/")
def create_pickup(
    current_user: User = Depends(require_permission("pickup.create"))
):
    return {"message": "Pickup created"}
