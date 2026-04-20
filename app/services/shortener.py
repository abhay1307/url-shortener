import random
import string

from sqlalchemy.orm import Session

from app.models import URL

CHARS = string.ascii_letters + string.digits  # 62 chars → 62^6 = 56.8B combinations


def generate_code(length: int = 6) -> str:
    return "".join(random.choices(CHARS, k=length))


def create_short_url(db: Session, original_url: str) -> URL:
    """
    Generate a unique Base62 short code and persist to DB.
    Retries up to 5 times on collision (astronomically rare at scale).
    """
    for _ in range(5):
        code = generate_code()
        existing = db.query(URL).filter(URL.short_code == code).first()
        if not existing:
            url_obj = URL(original_url=original_url, short_code=code)
            db.add(url_obj)
            db.commit()
            db.refresh(url_obj)
            return url_obj

    raise RuntimeError("Failed to generate a unique short code after 5 attempts")


def get_url_by_code(db: Session, code: str) -> URL | None:
    return db.query(URL).filter(URL.short_code == code).first()
