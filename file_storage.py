import os
import logging
import uuid
from pathlib import Path
from typing import Optional, Tuple
import shutil

logger = logging.getLogger(__name__)

class FileStorageService:
    def __init__(self):
        # Storage directory - works for local, Docker volume, and K8s persistent volume
        self.storage_dir = Path(os.getenv("STORAGE_DIR", "./uploaded_images"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File storage initialized: {self.storage_dir.absolute()}")
    
    def save_uploaded_file(self, file_bytes: bytes, original_filename: str, user_id: int, building_id: int) -> Tuple[str, str]:
        """
        Save uploaded file and return (file_id, file_path)
        
        Args:
            file_bytes: Raw file content
            original_filename: Original filename from upload
            user_id: User who uploaded the file
            building_id: Building the file belongs to
            
        Returns:
            Tuple of (unique_file_id, relative_file_path)
        """
        try:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Extract file extension
            file_ext = Path(original_filename).suffix.lower()
            if not file_ext:
                file_ext = '.png'  # Default extension
            
            # Create organized directory structure: user_id/building_id/
            user_dir = self.storage_dir / str(user_id) / str(building_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename: file_id + original_extension
            filename = f"{file_id}{file_ext}"
            file_path = user_dir / filename
            
            # Save the file
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            # Return relative path for database storage
            relative_path = f"{user_id}/{building_id}/{filename}"
            
            logger.info(f"Saved file: {original_filename} -> {relative_path}")
            return file_id, relative_path
            
        except Exception as e:
            logger.error(f"Failed to save file {original_filename}: {e}")
            raise
    
    def get_file_path(self, relative_path: str) -> Optional[Path]:
        """
        Get absolute file path from relative path
        
        Args:
            relative_path: Relative path stored in database (e.g., "1/2/uuid.png")
            
        Returns:
            Absolute path to file, or None if not found
        """
        try:
            full_path = self.storage_dir / relative_path
            
            if full_path.exists() and full_path.is_file():
                return full_path
            else:
                logger.warning(f"File not found: {relative_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error accessing file {relative_path}: {e}")
            return None
    
    def delete_file(self, relative_path: str) -> bool:
        """
        Delete a file from storage
        
        Args:
            relative_path: Relative path stored in database
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            full_path = self.storage_dir / relative_path
            
            if full_path.exists():
                full_path.unlink()
                logger.info(f"Deleted file: {relative_path}")
                
                # Clean up empty directories
                try:
                    full_path.parent.rmdir()  # Remove building dir if empty
                    full_path.parent.parent.rmdir()  # Remove user dir if empty
                except OSError:
                    pass  # Directories not empty, which is fine
                
                return True
            else:
                logger.warning(f"File not found for deletion: {relative_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file {relative_path}: {e}")
            return False
    
    def get_storage_info(self) -> dict:
        """Get storage system information"""
        try:
            total_files = sum(1 for _ in self.storage_dir.rglob('*') if _.is_file())
            total_size = sum(f.stat().st_size for f in self.storage_dir.rglob('*') if f.is_file())
            
            return {
                "storage_dir": str(self.storage_dir.absolute()),
                "total_files": total_files,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        except Exception as e:
            logger.error(f"Error getting storage info: {e}")
            return {"error": str(e)}

# Global file storage instance
file_storage = FileStorageService()