import io
import base64
import logging
from pathlib import Path
from typing import Tuple, Optional
import fitz  # PyMuPDF
from PIL import Image
from config import Config

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.max_size = Config.MAX_FILE_SIZE
        self.allowed_extensions = Config.ALLOWED_EXTENSIONS
    
    def validate_file(self, filename: str, content_length: int) -> bool:
        file_ext = Path(filename).suffix.lower()
        
        if file_ext not in self.allowed_extensions:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        if content_length > self.max_size:
            raise ValueError(f"File size {content_length} exceeds maximum {self.max_size}")
        
        return True
    
    def process_pdf(self, pdf_bytes: bytes) -> Tuple[str, str]:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            # Extract text
            text_content = ""
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_content += page.get_text()
            
            # Convert first page to image for vision analysis
            page = doc[0]  # First page
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
            img_data = pix.tobytes("png")
            
            # Convert to base64 for OpenAI API
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            doc.close()
            logger.info(f"Processed PDF: {len(doc)} pages, {len(text_content)} characters of text")
            
            return img_base64, text_content
            
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            raise ValueError(f"Failed to process PDF: {e}")
    
    def process_image(self, image_bytes: bytes) -> str:
        try:
            # Open and validate image
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large (max 2048x2048 for OpenAI)
            max_size = (2048, 2048)
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized image to {image.size}")
            
            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            logger.info(f"Processed image: {image.size}, {len(img_base64)} base64 chars")
            
            return img_base64
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            raise ValueError(f"Failed to process image: {e}")
    
    def process_file(self, filename: str, file_bytes: bytes) -> Tuple[str, Optional[str]]:
        self.validate_file(filename, len(file_bytes))
        
        file_ext = Path(filename).suffix.lower()
        
        if file_ext == '.pdf':
            return self.process_pdf(file_bytes)
        elif file_ext in {'.png', '.jpg', '.jpeg'}:
            image_b64 = self.process_image(file_bytes)
            return image_b64, None
        else:
            raise ValueError(f"Unsupported file extension: {file_ext}")