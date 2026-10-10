"""Feedback from testers and first users (the web's /opinion page and the app)."""

from fastapi import APIRouter, Depends, status

from app.api.schemas import FeedbackRequest, FeedbackResponse
from app.core.security import get_optional_user
from app.repositories import FeedbackRecord, Repository, UserRecord, get_repository

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def send_feedback(
    request: FeedbackRequest,
    user: UserRecord | None = Depends(get_optional_user),
    repository: Repository = Depends(get_repository),
):
    """Stores a message. Signed-in users are linked by uid; `website` is a honeypot that bots fill in."""
    if request.website:
        # Pretend it worked so the bot does not retry.
        return {"id": "", "received": True}
    saved = await repository.save_feedback(
        FeedbackRecord(
            message=request.message.strip(),
            rating=request.rating,
            email=(request.email or "").strip() or (user.email if user else None),
            page=request.page,
            source=request.source,
            user_id=user.id if user else None,
        )
    )
    return {"id": saved.id, "received": True}
