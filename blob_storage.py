import os
import logging
import uuid
from typing import Optional, Tuple
from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import AzureError
from config import Config

logger = logging.getLogger(__name__)

class BlobStorageService:
    def __init__(self):
        self.config = Config()
        
        # Azure Blob Storage configuration
        self.account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "uploaded-images")
        
        # Initialize blob client
        if self.account_name:
            # Production: Use managed identity or connection string
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if connection_string:
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
                logger.info("Initialized Azure Blob Storage with connection string")
            else:
                # Use managed identity for production
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()
                account_url = f"https://{self.account_name}.blob.core.windows.net"
                self.blob_service_client = BlobServiceClient(account_url=account_url, credential=credential)
                logger.info("Initialized Azure Blob Storage with managed identity")
        else:
            # Local development fallback - use file system
            self.blob_service_client = None
            logger.warning("Azure Blob Storage not configured, using local file storage fallback")
            
            # Import and use local file storage
            from file_storage import FileStorageService
            self.local_storage = FileStorageService()
    
    def save_uploaded_file(self, file_bytes: bytes, original_filename: str, user_id: int, building_id: int) -> Tuple[str, str]:
        """
        Save uploaded file to Azure Blob Storage
        
        Returns:
            Tuple of (unique_file_id, blob_url)
        """
        try:
            if not self.blob_service_client:
                # Fallback to local storage for development
                return self.local_storage.save_uploaded_file(file_bytes, original_filename, user_id, building_id)
            
            # Generate unique file ID and blob name
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(original_filename)[1].lower()
            
            # Organize blobs: users/{user_id}/buildings/{building_id}/{file_id}{ext}
            blob_name = f"users/{user_id}/buildings/{building_id}/{file_id}{file_extension}"
            
            # Determine content type
            content_type_map = {
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.pdf': 'application/pdf'
            }
            content_type = content_type_map.get(file_extension, 'application/octet-stream')
            
            # Upload to blob storage
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(
                file_bytes,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )
            
            # Generate public URL
            blob_url = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}"
            
            logger.info(f"Uploaded file to blob storage: {original_filename} -> {blob_name}")
            return file_id, blob_url
            
        except AzureError as e:
            logger.error(f"Azure Blob Storage error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to save file to blob storage: {e}")
            raise
    
    def get_blob_url(self, blob_path: str) -> Optional[str]:
        """
        Get public URL for a blob
        
        Args:
            blob_path: Either blob name or full URL
            
        Returns:
            Public blob URL or None if not found
        """
        try:
            if not self.blob_service_client:
                # Local storage fallback
                file_path = self.local_storage.get_file_path(blob_path)
                return f"/local-files/{blob_path}" if file_path else None
            
            # If already a full URL, return as-is
            if blob_path.startswith('https://'):
                return blob_path
            
            # Generate URL from blob name
            return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_path}"
            
        except Exception as e:
            logger.error(f"Error getting blob URL: {e}")
            return None
    
    def delete_blob(self, blob_path: str) -> bool:
        """
        Delete a blob from storage
        
        Args:
            blob_path: Blob name or full URL
            
        Returns:
            True if deleted successfully
        """
        try:
            if not self.blob_service_client:
                # Local storage fallback
                return self.local_storage.delete_file(blob_path)
            
            # Extract blob name from URL if needed
            if blob_path.startswith('https://'):
                blob_name = blob_path.split('/')[-1]
            else:
                blob_name = blob_path
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.delete_blob()
            logger.info(f"Deleted blob: {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting blob: {e}")
            return False
    
    def get_storage_info(self) -> dict:
        """Get storage system information"""
        try:
            if not self.blob_service_client:
                return self.local_storage.get_storage_info()
            
            # Count blobs in container
            blob_list = self.blob_service_client.get_container_client(self.container_name).list_blobs()
            blob_count = sum(1 for _ in blob_list)
            
            return {
                "storage_type": "azure_blob",
                "account_name": self.account_name,
                "container_name": self.container_name,
                "total_blobs": blob_count
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {"error": str(e)}

# Global blob storage instance
blob_storage = BlobStorageService()