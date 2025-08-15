import os
import uuid
from PIL import Image
import requests
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self, storage_path: str = "static/images"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
    
    def save_image_from_url(self, image_url: str, filename: str = None) -> str:
        """Download and save image from URL"""
        try:
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Generate filename if not provided
            if not filename:
                filename = f"{uuid.uuid4()}.jpg"
            
            filepath = os.path.join(self.storage_path, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Image saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving image from URL: {e}")
            raise
    
    def save_uploaded_image(self, image_data: bytes, filename: str = None) -> str:
        """Save uploaded image data"""
        try:
            if not filename:
                filename = f"{uuid.uuid4()}.jpg"
            
            filepath = os.path.join(self.storage_path, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"Uploaded image saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving uploaded image: {e}")
            raise
    
    def resize_image(self, filepath: str, size: tuple, output_path: str = None) -> str:
        """Resize image to specified dimensions"""
        try:
            with Image.open(filepath) as img:
                resized_img = img.resize(size, Image.Resampling.LANCZOS)
                
                if not output_path:
                    name, ext = os.path.splitext(filepath)
                    output_path = f"{name}_resized{ext}"
                
                resized_img.save(output_path)
                logger.info(f"Image resized: {output_path}")
                return output_path
                
        except Exception as e:
            logger.error(f"Error resizing image: {e}")
            raise
    
    def optimize_for_platform(self, filepath: str, platform: str) -> str:
        """Optimize image for specific social media platform"""
        try:
            platform_sizes = {
                'instagram': (1080, 1080),  # Square post
                'twitter': (1200, 675),     # Twitter card
                'facebook': (1200, 630),    # Facebook post
                'linkedin': (1200, 627)     # LinkedIn post
            }
            
            size = platform_sizes.get(platform.lower(), (1200, 675))
            
            name, ext = os.path.splitext(filepath)
            output_path = f"{name}_{platform}{ext}"
            
            return self.resize_image(filepath, size, output_path)
            
        except Exception as e:
            logger.error(f"Error optimizing image for {platform}: {e}")
            raise
    
    def get_image_info(self, filepath: str) -> Dict:
        """Get image information"""
        try:
            with Image.open(filepath) as img:
                return {
                    'size': img.size,
                    'format': img.format,
                    'mode': img.mode,
                    'filename': os.path.basename(filepath)
                }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}