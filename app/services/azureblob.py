from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions
)
from azure.core.exceptions import ResourceNotFoundError
from datetime import datetime, timedelta
import uuid
from app.core.config import settings
from urllib.parse import urlparse


AZURE_STORAGE_CONNECTION_STRING=settings.AZURE_STORAGE_CONNECTION_STRING
AZURE_CONTAINER_NAME=settings.AZURE_CONTAINER_NAME
AZURE_ACCOUNT_KEY=settings.AZURE_ACCOUNT_KEY

class AzureBlobService:
    def __init__(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        self.container_client = self.blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        self.account_name = self.blob_service_client.account_name
        self.container_name = AZURE_CONTAINER_NAME
        self.account_key = AZURE_ACCOUNT_KEY  # needed for SAS

    # UPLOAD
    async def upload_image(self, file, folder: str):

        extension = file.filename.split(".")[-1]
        blob_name = f"{folder}/{uuid.uuid4()}.{extension}"

        blob_client = self.container_client.get_blob_client(blob_name)

        content = await file.read()
        blob_client.upload_blob(content, overwrite=True)

        return {
            "blob_name": blob_name,
            "url": self.get_blob_url(blob_name)
        }

    #  GET URL
    def get_blob_url(self, blob_name: str):
        blob_client = self.container_client.get_blob_client(blob_name)
        return blob_client.url  # works if container is public

    # GET SAS URL (PRIVATE)
    def get_sas_url(self, blob_name: str, expiry_minutes: int = 60):
        if not self.account_key:
            raise Exception("Account key required for SAS")

        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(minutes=expiry_minutes)
        )

        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"

    # DELETE
    def delete_image(self, blob_name: str):
        blob_client = self.container_client.get_blob_client(blob_name)
        try:
            blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False

    # LIST 
    def list_images(self):
        blobs = self.container_client.list_blobs()
        return [blob.name for blob in blobs]
    
    #  LIST BY FOLDER NAME
    def list_images_by_folder(self, folder: str):
        blobs = self.container_client.list_blobs(name_starts_with=f"{folder}/")
        return [blob.name for blob in blobs]
    
    # Get blob_name from url
    def get_blob_name_from_url(self, url: str) -> str:
        path = urlparse(url).path  # /images/products/abc.jpg

        # remove leading slash
        path = path.lstrip("/")

        # remove container name
        if path.startswith(AZURE_CONTAINER_NAME + "/"):
            return path[len(AZURE_CONTAINER_NAME) + 1:]

        raise ValueError("Invalid Azure blob URL")