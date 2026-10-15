from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.notification import Notification
from ..models.user import User
from ..schemas.booking import NotificationOut
from ..security import get_current_user
from ..services.serializers import notification_to_dict

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/me", response_model=list[NotificationOut])
def my_notifications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc()).limit(100)
    )
    return [notification_to_dict(n) for n in rows]


@router.get("/me/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return {"count": count or 0}


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    n.is_read = True
    db.commit()
    db.refresh(n)
    return notification_to_dict(n)


@router.post("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False)))
    count = 0
    for n in rows:
        n.is_read = True
        count += 1
    db.commit()
    return {"marked_read": count}