from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from .database import Base


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    character = Column(String(10), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)

    images = relationship(
        "CharacterImage",
        back_populates="character",
        cascade="all, delete-orphan",
        order_by="CharacterImage.display_order"
    )


class CharacterImage(Base):
    __tablename__ = "character_images"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), index=True, nullable=False)
    image_path = Column(String(500), nullable=False)
    source_text = Column(Text, default="")
    display_order = Column(Integer, default=0)

    character = relationship("Character", back_populates="images")

    __table_args__ = (
        Index("idx_character_images_character_id", "character_id"),
    )
