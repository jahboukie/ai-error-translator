import os
import io
import logging
from typing import Optional
from google.cloud import vision
from PIL import Image
import base64

from app.config import settings

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self):
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Google Vision API client"""
        try:
            if settings.GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = settings.GOOGLE_APPLICATION_CREDENTIALS
                self.client = vision.ImageAnnotatorClient()
                logger.info("Google Vision API client initialized successfully")
            else:
                logger.warning("Google Vision API credentials not found. OCR functionality will be limited.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Vision API client: {str(e)}")
            self.client = None
    
    async def extract_text_from_image(self, image_data: bytes) -> str:
        """
        Extract text from image using Google Vision API
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Extracted text string
        """
        if not self.client:
            raise Exception("Google Vision API client not initialized")
        
        try:
            # Validate image size
            if len(image_data) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise Exception(f"Image size exceeds {settings.MAX_IMAGE_SIZE_MB}MB limit")
            
            # Validate image format
            image = Image.open(io.BytesIO(image_data))
            if image.format.lower() not in ['jpeg', 'jpg', 'png', 'webp']:
                raise Exception("Unsupported image format. Use JPEG, PNG, or WebP.")
            
            # Create Vision API image object
            vision_image = vision.Image(content=image_data)
            
            # Perform text detection
            response = self.client.text_detection(image=vision_image)
            
            if response.error.message:
                raise Exception(f"Vision API error: {response.error.message}")
            
            # Extract text annotations
            texts = response.text_annotations
            
            if not texts:
                return ""
            
            # Return the first (most comprehensive) text annotation
            extracted_text = texts[0].description
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from image")
            return extracted_text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            raise Exception(f"Text extraction failed: {str(e)}")
    
    async def extract_text_from_base64(self, base64_image: str) -> str:
        """
        Extract text from base64-encoded image
        
        Args:
            base64_image: Base64-encoded image string
            
        Returns:
            Extracted text string
        """
        try:
            # Remove data URL prefix if present
            if base64_image.startswith('data:image'):
                base64_image = base64_image.split(',')[1]
            
            # Decode base64 to bytes
            image_data = base64.b64decode(base64_image)
            
            return await self.extract_text_from_image(image_data)
            
        except Exception as e:
            logger.error(f"Error extracting text from base64 image: {str(e)}")
            raise Exception(f"Base64 text extraction failed: {str(e)}")
    
    def preprocess_image(self, image_data: bytes) -> bytes:
        """
        Preprocess image for better OCR results
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Preprocessed image bytes
        """
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large
            max_dimension = 2048
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = tuple(int(dim * ratio) for dim in image.size)
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save preprocessed image
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=90)
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            return image_data  # Return original if preprocessing fails
    
    async def health_check(self) -> dict:
        """
        Check the health of the Vision service
        
        Returns:
            Health status dictionary
        """
        try:
            if not self.client:
                return {"status": "unhealthy", "reason": "Client not initialized"}
            
            # Try a simple operation to test connectivity
            # Create a minimal test image (1x1 pixel)
            test_image_data = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
            )
            
            vision_image = vision.Image(content=test_image_data)
            response = self.client.text_detection(image=vision_image)
            
            if response.error.message:
                return {"status": "unhealthy", "reason": response.error.message}
            
            return {"status": "healthy"}
            
        except Exception as e:
            logger.error(f"Vision service health check failed: {str(e)}")
            return {"status": "unhealthy", "reason": str(e)}