from fastapi import APIRouter
import os

router = APIRouter()

# Intentional vulnerability: no authentication on admin endpoints
@router.get("/admin/users")
def list_all_users():
    return {"users": ["admin", "user1", "user2"]}

@router.delete("/admin/users/{user_id}")
def delete_user(user_id: str):
    return {"deleted": user_id}

@router.get("/admin/run")
def run_command(cmd: str):
    # Intentional vulnerability: command injection
    result = os.system(cmd)
    return {"result": result}
