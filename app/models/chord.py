from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ChordModel(Base):
    __tablename__ = "chords"

    id = Column(Integer, primary_key=True, autoincrement=True)
    root = Column(String(2), nullable=False)
    chord_type = Column(String(10), nullable=False)
    triad = Column(String(50), nullable=False)
    circle_position = Column(Integer, nullable=False)
