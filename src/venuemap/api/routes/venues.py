from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from venuemap.api.deps import get_db
from venuemap.api.schemas import VenueResponse
from venuemap.db.models import Venue

router = APIRouter()


@router.get("/venues", response_model=list[VenueResponse])
def get_venues(db: Session = Depends(get_db)):
    venues = db.query(Venue).options(joinedload(Venue.city)).all()
    return [
        VenueResponse(
            slug=v.slug,
            name=v.name,
            city=v.city.name,
            latitude=v.latitude,
            longitude=v.longitude,
        )
        for v in venues
    ]
