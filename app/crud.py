from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models


def get_character_by_name(db: Session, character: str):
    return (
        db.query(models.Character)
        .filter(models.Character.character == character)
        .first()
    )


def get_all_characters_with_counts(db: Session):
    return (
        db.query(
            models.Character.character,
            func.count(models.CharacterImage.id).label("total_images")
        )
        .join(models.CharacterImage)
        .group_by(models.Character.id)
        .order_by(models.Character.character)
        .all()
    )


def get_or_create_character(db: Session, character: str, description: str = None):
    """获取或创建字符，处理并发重复插入"""
    db_char = get_character_by_name(db, character)
    if db_char is not None:
        return db_char
    try:
        db_char = models.Character(character=character, description=description)
        db.add(db_char)
        db.commit()
        db.refresh(db_char)
        return db_char
    except Exception:
        db.rollback()
        db_char = get_character_by_name(db, character)
        if db_char is None:
            raise
        return db_char


def create_character(db: Session, character: str, description: str = None):
    db_char = models.Character(character=character, description=description)
    db.add(db_char)
    db.commit()
    db.refresh(db_char)
    return db_char


def create_character_image(
    db: Session,
    character_id: int,
    image_path: str,
    source_text: str,
    display_order: int = 0
):
    db_img = models.CharacterImage(
        character_id=character_id,
        image_path=image_path,
        source_text=source_text,
        display_order=display_order
    )
    db.add(db_img)
    return db_img


def delete_character_images(db: Session, character_id: int):
    db.query(models.CharacterImage).filter(
        models.CharacterImage.character_id == character_id
    ).delete()
    db.commit()
