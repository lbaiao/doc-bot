from fastapi import APIRouter

from app.core.security import fastapi_users
from app.db.schemas.user import UserRead, UserUpdate

router = APIRouter()

# Include fastapi-users user management routes
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
