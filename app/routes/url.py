from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.cache import cache_url, get_cached_url
from app.services.publisher import publish_click
from app.services.shortener import create_short_url, get_url_by_code
from app.config import settings

router = APIRouter()


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


@router.post("/api/shorten", response_model=ShortenResponse)
def shorten_url(req: ShortenRequest, db: Session = Depends(get_db)):
    original = str(req.url)
    url_obj = create_short_url(db, original)
    cache_url(url_obj.short_code, original)
    return ShortenResponse(
        short_code=url_obj.short_code,
        short_url=f"{settings.base_url}/{url_obj.short_code}",
        original_url=original,
    )


@router.get("/{code}")
def redirect_url(code: str, request: Request, db: Session = Depends(get_db)):
    # 1. Check Redis cache first (fast path)
    cached = get_cached_url(code)
    if cached:
        _fire_click(code, request)
        return RedirectResponse(url=cached, status_code=302)

    # 2. Cache miss → query PostgreSQL
    url_obj = get_url_by_code(db, code)
    if not url_obj:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # 3. Warm the cache for next request
    cache_url(code, url_obj.original_url)
    _fire_click(code, request)
    return RedirectResponse(url=url_obj.original_url, status_code=302)


def _fire_click(code: str, request: Request) -> None:
    ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "")
    referrer = request.headers.get("Referer", "")
    ua = request.headers.get("User-Agent", "")
    publish_click(code, ip_address=ip, referrer=referrer, user_agent=ua)
