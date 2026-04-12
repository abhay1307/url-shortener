from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from database import SessionLocal
from models import URL
from utils import encode
import redis 
import json
from producer import publish_click

app = FastAPI()

r = redis.Redis(host="redis", port=6379, decode_response=True)

def get_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/shorten")
def shorten_url(original_url: str):
    db: Session = next(get_db())

    url = URL(original_url=original_url)
    db.add(url)
    db.commit()
    db.refresh(url)

    short_code = encode(url.id)
    url.short_code = short_code
    db.commit()

    return {"short_url": f"http://localhost:800/{short_code}"}

@app.get("/{code}")
def redirect(code.str):
    #check redis for code
    cached = r.get(code)
    if cached:
        published_click(code)
        return RedirectResponse(cached)

    db : Session = next(get_db())
    url = db.query(URL).filter(URL.short_code == code).first()

    if not url:
        raise HTTPException(404)

    #cache it
    r.setex(code, 86400, url.original_url)

    return RedirectResponse(url.original_url)