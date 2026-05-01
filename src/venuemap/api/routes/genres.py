from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from venuemap.api.deps import get_db
from venuemap.db.models import Genre

router = APIRouter()


@router.get("/genres", response_model=list[str])
def get_genres(db: Session = Depends(get_db)):
    rows = db.query(Genre.name).order_by(Genre.name).all()
    return [row.name for row in rows]
