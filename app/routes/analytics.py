from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Click, URL
from app.services.cache import get_cache_stats

router = APIRouter(prefix="/api/analytics")


@router.get("/{code}")
def get_analytics(code: str, db: Session = Depends(get_db)):
    url_obj = db.query(URL).filter(URL.short_code == code).first()
    if not url_obj:
        raise HTTPException(status_code=404, detail="Short code not found")

    clicks = (
        db.query(Click)
        .filter(Click.short_code == code)
        .order_by(Click.clicked_at.desc())
        .all()
    )

    total = len(clicks)

    # Clicks in last 24h
    since_24h = datetime.utcnow() - timedelta(hours=24)
    last_24h = sum(1 for c in clicks if c.clicked_at and c.clicked_at.replace(tzinfo=None) > since_24h)

    # Device breakdown
    devices = Counter(c.device_type or "unknown" for c in clicks)

    # Top referrers
    referrers = Counter(
        (c.referrer or "direct") for c in clicks if c.referrer != ""
    )
    top_referrers = [
        {"referrer": r, "count": n} for r, n in referrers.most_common(5)
    ]

    # Clicks by hour (last 24h)
    hourly: dict[str, int] = {}
    for c in clicks:
        if c.clicked_at:
            hour_key = c.clicked_at.strftime("%Y-%m-%dT%H:00")
            hourly[hour_key] = hourly.get(hour_key, 0) + 1

    recent = [
        {
            "clicked_at": c.clicked_at,
            "ip_address": c.ip_address,
            "referrer": c.referrer or "direct",
            "device_type": c.device_type or "unknown",
        }
        for c in clicks[:20]
    ]

    return {
        "short_code": code,
        "original_url": url_obj.original_url,
        "created_at": url_obj.created_at,
        "total_clicks": total,
        "clicks_last_24h": last_24h,
        "device_breakdown": dict(devices),
        "top_referrers": top_referrers,
        "hourly_clicks": hourly,
        "recent_clicks": recent,
    }


@router.get("")
def get_all_urls(db: Session = Depends(get_db)):
    urls = db.query(URL).order_by(URL.created_at.desc()).limit(50).all()
    result = []
    for u in urls:
        count = db.query(func.count(Click.id)).filter(Click.short_code == u.short_code).scalar()
        result.append(
            {
                "short_code": u.short_code,
                "original_url": u.original_url,
                "created_at": u.created_at,
                "total_clicks": count,
            }
        )
    return result


@router.get("/system/stats")
def get_system_stats(db: Session = Depends(get_db)):
    total_urls = db.query(func.count(URL.id)).scalar()
    total_clicks = db.query(func.count(Click.id)).scalar()
    cache = get_cache_stats()
    return {
        "total_urls": total_urls,
        "total_clicks": total_clicks,
        "cache": cache,
    }
