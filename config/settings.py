
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    
    # Database Configuration
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    QDRANT_URL = os.getenv('QDRANT_URL')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    
    # AI Model Configuration
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Flask Configuration
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Social Media API Keys
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN = os.getenv('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_TOKEN_SECRET = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    
    FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
    LINKEDIN_ACCESS_TOKEN = os.getenv('LINKEDIN_ACCESS_TOKEN')
    INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    
    # MCP Configuration
    os.environ['CREWAI_DISABLE_TELEMETRY'] = 'true'
    os.environ['OTEL_SDK_DISABLED'] = 'true'
    MCP_HOST = os.getenv('MCP_HOST', 'localhost')
    MCP_PORT = int(os.getenv('MCP_PORT', 8001))
    
    # File Storage
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    IMAGE_FOLDER = os.getenv('IMAGE_FOLDER', 'static/images')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    
    # Platform Configurations
    PLATFORM_CONFIGS = {
        'twitter': {
            'max_length': 280,
            'max_hashtags': 3,
            'image_sizes': [(1200, 675)],
            'supported_formats': ['jpg', 'png', 'gif'],
            'optimal_posting_times': ['09:00', '15:00', '18:00']
        },
        'linkedin': {
            'max_length': 3000,
            'max_hashtags': 5,
            'image_sizes': [(1200, 627)],
            'supported_formats': ['jpg', 'png'],
            'optimal_posting_times': ['08:00', '12:00', '17:00']
        },
        'facebook': {
            'max_length': 2000,
            'max_hashtags': 3,
            'image_sizes': [(1200, 630)],
            'supported_formats': ['jpg', 'png', 'gif', 'mp4'],
            'optimal_posting_times': ['13:00', '15:00', '19:00']
        },
        'instagram': {
            'max_length': 2200,
            'max_hashtags': 15,
            'image_sizes': [(1080, 1080), (1080, 1350)],
            'supported_formats': ['jpg', 'png'],
            'optimal_posting_times': ['11:00', '14:00', '17:00']
        }
    }
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/content_system.log')
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration"""
        required_vars = [
            'QDRANT_URL', 'QDRANT_API_KEY', 'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True