from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db, utcnow
from ..models.mentor import Mentor
from ..models.user import User
from ..schemas.mentor import VerificationOut, VerificationQueueItem, VerificationReviewIn
from ..security import require_role
from ..services.serializers import verification_queue_item, verification_to_dict

router = APIRouter(prefix="/admin", tags=["Admin"])


def _get_mentor_or_404(db: Session, mentor_id: int) -> Mentor:
    mentor = db.get(Mentor, mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor not found.")
    return mentor


@router.get("/verifications", response_model=list[VerificationQueueItem])
def list_verifications(
    status_filter: str = "pending",
    admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """status_filter: pending | verified | rejected | unverified | all."""
    stmt = select(Mentor)
    if status_filter != "all":
        stmt = stmt.where(Mentor.verification_status == status_filter)
    rows = db.scalars(stmt.order_by(Mentor.verification_submitted_at.desc().nullslast()))
    return [verification_queue_item(m) for m in rows]


@router.get("/verifications/{mentor_id}/document")
def download_verification_document(mentor_id: int, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Streams the uploaded credential file. Admin-only: these are personal documents."""
    mentor = _get_mentor_or_404(db, mentor_id)
    if not mentor.verification_document_data:
        raise HTTPException(status_code=404, detail="No document has been uploaded for this mentor.")
    return Response(
        content=mentor.verification_document_data,
        media_type=mentor.verification_document_mime or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{mentor.verification_document_name or "document"}"'},
    )


@router.post("/verifications/{mentor_id}/approve", response_model=VerificationOut)
def approve_verification(mentor_id: int, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    mentor = _get_mentor_or_404(db, mentor_id)
    if mentor.verification_status != "pending":
        raise HTTPException(status_code=409, detail=f"This mentor is '{mentor.verification_status}', not pending review.")
    mentor.verification_status = "verified"
    mentor.verification_rejection_reason = None
    mentor.verification_reviewed_at = utcnow().isoformat()
    mentor.verification_reviewed_by = admin.full_name
    db.commit()
    db.refresh(mentor)
    return verification_to_dict(mentor)


@router.post("/verifications/{mentor_id}/reject", response_model=VerificationOut)
def reject_verification(mentor_id: int, payload: VerificationReviewIn, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    mentor = _get_mentor_or_404(db, mentor_id)
    if mentor.verification_status != "pending":
        raise HTTPException(status_code=409, detail=f"This mentor is '{mentor.verification_status}', not pending review.")
    if not payload.reason or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="A reason is required when rejecting a verification request.")
    mentor.verification_status = "rejected"
    mentor.verification_rejection_reason = payload.reason.strip()
    mentor.verification_reviewed_at = utcnow().isoformat()
    mentor.verification_reviewed_by = admin.full_name
    db.commit()
    db.refresh(mentor)
    return verification_to_dict(mentor)