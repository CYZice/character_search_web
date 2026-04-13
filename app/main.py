from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import os

from . import models, crud, database


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=database.engine)
    yield


app = FastAPI(title="汉字字形检索系统", lifespan=lifespan)

# Serve static image files from data directory
data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
if os.path.exists(data_dir):
    app.mount("/images", StaticFiles(directory=data_dir), name="images")

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/characters/{character}")
def search_character(character: str, db: Session = Depends(database.get_db)):
    db_char = crud.get_character_by_name(db, character)
    if db_char is None:
        raise HTTPException(status_code=404, detail=f"Character '{character}' not found")

    images = sorted(db_char.images, key=lambda x: x.display_order)
    return {
        "character": db_char.character,
        "total_images": len(images),
        "images": [
            {
                "id": img.id,
                "image_url": f"/images/{img.image_path}",
                "source_text": img.source_text,
                "display_order": img.display_order
            }
            for img in images
        ]
    }


@app.get("/api/characters")
def list_characters(db: Session = Depends(database.get_db)):
    results = crud.get_all_characters_with_counts(db)
    return {
        "characters": [
            {"character": r.character, "total_images": r.total_images}
            for r in results
        ]
    }
