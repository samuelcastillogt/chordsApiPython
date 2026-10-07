"""Account endpoints. Sign-up and sign-in happen in Firebase; the API only sees ID tokens."""

from fastapi import APIRouter, Depends, Response, status

from app.api.schemas import UserResponse, UserUpdateRequest
from app.core.security import get_current_user
from app.repositories import Repository, UserRecord, get_repository

router = APIRouter()


def serialize_user(user: UserRecord) -> dict:
    return {"id": user.id, "email": user.email, "displayName": user.display_name, "photoUrl": user.photo_url}


@router.get("/auth/me", response_model=UserResponse)
async def me(user: UserRecord = Depends(get_current_user)):
    """The signed-in user; the first call after signing up creates the account."""
    return serialize_user(user)


@router.patch("/auth/me", response_model=UserResponse)
async def update_me(
    request: UserUpdateRequest, user: UserRecord = Depends(get_current_user), repository: Repository = Depends(get_repository)
):
    if "displayName" in request.model_fields_set:
        user.display_name = (request.displayName or "").strip() or None
        await repository.save_user(user)
    return serialize_user(user)


@router.delete("/auth/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: UserRecord = Depends(get_current_user), repository: Repository = Depends(get_repository)):
    """Deletes the user's data (progressions included). The Firebase account is deleted by the client."""
    await repository.delete_user(user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
