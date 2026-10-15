import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.roadmap import Milestone, Roadmap
from ..models.user import User
from ..schemas.roadmap import GenerateIn, MilestoneOut, MilestoneUpdate, RoadmapOut
from ..security import get_current_user
from ..services.ai_service import generate_roadmap
from ..services.serializers import milestone_to_dict, roadmap_to_dict

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])


def _owned_roadmap(db: Session, roadmap_id: int, user: User) -> Roadmap:
    roadmap = db.get(Roadmap, roadmap_id)
    if not roadmap or roadmap.user_id != user.id:
        raise HTTPException(status_code=404, detail="Roadmap not found.")
    return roadmap


@router.post("/generate", response_model=RoadmapOut, status_code=status.HTTP_201_CREATED)
def generate(payload: GenerateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    goal = " ".join(payload.goal.split())
    result = generate_roadmap(goal)  # never raises

    if result["invalid_reason"]:
        raise HTTPException(status_code=422, detail=result["invalid_reason"])

    roadmap = Roadmap(user_id=user.id, goal=goal, source=result["source"], error_message=result["error"])
    for i, ms in enumerate(result["milestones"], start=1):
        roadmap.milestones.append(
            Milestone(
                position=i,
                title=ms["title"],
                description=ms["description"],
                topics=json.dumps(ms["topics"]),
                duration_weeks=ms["duration_weeks"],
            )
        )
    db.add(roadmap)

    if payload.replace_id:  # retry flow: swap out the roadmap the student is retrying
        old = db.get(Roadmap, payload.replace_id)
        if old and old.user_id == user.id:
            db.delete(old)

    db.commit()
    db.refresh(roadmap)
    return roadmap_to_dict(roadmap)


@router.get("/", response_model=list[RoadmapOut])
def list_roadmaps(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Roadmap).where(Roadmap.user_id == user.id).order_by(Roadmap.created_at.desc(), Roadmap.id.desc()))
    return [roadmap_to_dict(r) for r in rows]


@router.patch("/milestones/{milestone_id}", response_model=MilestoneOut)
def update_milestone(
    milestone_id: int, payload: MilestoneUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    milestone = db.get(Milestone, milestone_id)
    if not milestone or milestone.roadmap.user_id != user.id:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    milestone.status = payload.status
    db.commit()
    db.refresh(milestone)
    return milestone_to_dict(milestone)


@router.delete("/{roadmap_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roadmap(roadmap_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned_roadmap(db, roadmap_id, user))
    db.commit()
