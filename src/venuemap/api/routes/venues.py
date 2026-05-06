from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from venuemap.api.deps import get_db
from venuemap.api.schemas import VenueResponse
from venuemap.db.models import Venue

router = APIRouter()


@router.get("/venues", response_model=list[VenueResponse])
def get_venues(
    lat_min: float | None = Query(None),
    lat_max: float | None = Query(None),
    lng_min: float | None = Query(None),
    lng_max: float | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Venue).options(joinedload(Venue.city))

    if all(p is not None for p in (lat_min, lat_max, lng_min, lng_max)):
        q = q.filter(
            Venue.latitude >= lat_min,
            Venue.latitude <= lat_max,
            Venue.longitude >= lng_min,
            Venue.longitude <= lng_max,
        )

    return [
        VenueResponse(
            slug=v.slug,
            name=v.name,
            city=v.city.name,
            latitude=v.latitude,
            longitude=v.longitude,
        )
        for v in q.all()
    ]
