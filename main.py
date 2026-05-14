from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
import math

app = FastAPI(title="Aysu Art - Star Map API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class StarMapRequest(BaseModel):
    date: str
    lat: float
    lon: float

class Star(BaseModel):
    x: float
    y: float
    mag: float

class StarMapResponse(BaseModel):
    stars: List[Star]
    constellations: List[List[int]]
    sidereal_angle: float

@app.get("/")
def root():
    return {"status": "ok", "service": "Aysu Art Star Map API"}

@app.post("/api/starmap", response_model=StarMapResponse)
async def compute_starmap(req: StarMapRequest):
    try:
        d = datetime.fromisoformat(req.date.replace("Z", ""))
    except Exception:
        try:
            d = datetime.strptime(req.date, "%Y-%m-%d")
        except Exception:
            raise HTTPException(status_code=400, detail="Geçersiz tarih")

    seed = int(d.timestamp()) ^ int(req.lat * 1000) ^ int(req.lon * 1000)
    rng_state = [seed & 0xFFFFFFFF]

    def rnd():
        rng_state[0] = (1103515245 * rng_state[0] + 12345) & 0x7FFFFFFF
        return rng_state[0] / 0x7FFFFFFF

    day_of_year = d.timetuple().tm_yday
    sidereal = (day_of_year / 365.25) * 360.0 + req.lon

    stars: List[Star] = []
    n = 220
    for _ in range(n):
        r = math.sqrt(rnd()) * 0.48
        theta = rnd() * 2 * math.pi
        x = 0.5 + r * math.cos(theta)
        y = 0.5 + r * math.sin(theta)
        mag = (rnd() ** 2)
        stars.append(Star(x=x, y=y, mag=mag))

    constellations: List[List[int]] = []
    bright_indices = sorted(range(n), key=lambda i: -stars[i].mag)[:40]
    used = set()
    for _ in range(4):
        line: List[int] = []
        for idx in bright_indices:
            if idx not in used:
                line.append(idx)
                used.add(idx)
                break
        target_len = 3 + int(rnd() * 3)
        while len(line) < target_len:
            last = line[-1]
            lx, ly = stars[last].x, stars[last].y
            best = None
            best_d = 1e9
            for idx in bright_indices:
                if idx in used:
                    continue
                dx = stars[idx].x - lx
                dy = stars[idx].y - ly
                dd = dx * dx + dy * dy
                if dd < best_d and dd < 0.05:
                    best_d = dd
                    best = idx
            if best is None:
                break
            line.append(best)
            used.add(best)
        if len(line) >= 2:
            for i in range(len(line) - 1):
                constellations.append([line[i], line[i + 1]])

    return StarMapResponse(stars=stars, constellations=constellations, sidereal_angle=sidereal)
