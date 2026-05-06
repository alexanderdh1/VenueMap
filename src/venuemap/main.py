from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from venuemap.api.routes import events, genres, venues

app = FastAPI(title="VenueMap API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/api")
app.include_router(venues.router, prefix="/api")
app.include_router(genres.router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}
