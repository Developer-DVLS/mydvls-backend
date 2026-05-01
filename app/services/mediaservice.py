from fastapi import UploadFile
import uuid
import os
import shutil

from app.models.media import Media

class MediaService:

    @staticmethod
    async def save_image(file: UploadFile, image_file_name: str, db):
        upload_dir = f"static/images/{image_file_name}"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 1. Create a unique filename
        ext = file.filename.split(".")[-1]
        unique_name = f"{uuid.uuid4()}.{ext}"
        file_path = f"{upload_dir}/{unique_name}"
        
        # 2. Save file to disk (or S3)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Save record to DB
        new_media = Media(
            file_name=file.filename,
            file_path=f"/{file_path}",
            file_type=file.content_type,
        )
        db.add(new_media)
        await db.commit()
        await db.refresh(new_media)
        return new_media