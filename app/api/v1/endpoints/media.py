from typing import List
from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, File, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.media import MediaResponse
from app.core.database import get_db
from app.models.media import Media
from app.services.azureblob import AzureBlobService
from app.services.mediaservice import MediaService

media_router = APIRouter(prefix="/media", tags=["Media"])

@media_router.post("/upload")
async def upload_image(
    image_file_name: str = Form(...),
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
):
    return await MediaService.save_image(file, image_file_name, db)


@media_router.get("/media/{media_id}", response_model=MediaResponse)
async def get_media(media_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Media).where(Media.id == media_id))
    image = result.scalar_one_or_none()
    if not image:
        raise HTTPException(status_code=404, detail="Media not found")
    
    return image


@media_router.get("/", response_model=List[MediaResponse])
async def get_all_media(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Media)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()

@media_router.delete("/media/{media_id}")
async def delete_image(media_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Media).where(Media.id == media_id))
    image = result.scalar_one_or_none()
    if image:
        # Optional: Remove file from physical storage here
        await db.delete(image)
        await db.commit()
        return {"message": "Deleted successfully"}
    return {"error": "Not found"}


# azure blob container 

blob_service = AzureBlobService()

@media_router.post("/blob/upload")
async def upload(
    file: UploadFile = File(...),
    folder: str = Query(..., description="e.g. products, categories, offers")
):
    try:
        content = await file.read()

        # ensure bytes
        if not isinstance(content, bytes):
            raise HTTPException(status_code=400, detail="Invalid file format")

        blob_name = await blob_service.upload_image(content, file, folder)

        return {"blob_name": blob_name}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@media_router.get("/blob/images")
def get_images(
    folder: str = Query(...)
):
    try:
        images = blob_service.list_images_by_folder(folder)

        return {
            "folder": folder,
            "count": len(images),
            "images": [
                {
                    "blob_name": img,
                    "url": blob_service.get_blob_url(img)
                }
                for img in images
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@media_router.delete("/blob/images")
def delete_image(
    image_url: str = Query(...)
):
    try:
        # get blob_name 
        blob_name = blob_service.get_blob_name_from_url(image_url)
        
        success = blob_service.delete_image(blob_name)

        if not success:
            raise HTTPException(status_code=404, detail="Image not found")

        return {"message": "Deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# @media_router.get("/blob/images/url")
# def get_image_url(
#     blob_name: str = Query(...)
# ):
#     return {
#         "blob_name": blob_name,
#         "url": blob_service.get_blob_url(blob_name)
#     }