from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import base

class URL(Base) :
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Click(Base) :
    __tablename__ = "clicks"

    id = Column(Integer, primary_key=True)
    short_code = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    ip = Column(String)