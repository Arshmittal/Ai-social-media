import os
import sys
import asyncio
import threading
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import Config
from utils.logging_config import setup_logging
from database.mongodb_manager import MongoDBManager
from database.qdrant_manager import QdrantManager
from agents.crew_agents import ContentCrewManager
from services.social_media_service import SocialMediaService
from services.scheduler_service import SchedulerService
from services.image_service import ImageService
from mcp.mcp_server import MCPServer
from main import app
import logging

logger = logging.getLogger(__name__)

class ContentGenerationSystem:
    """Main system orchestrator"""
    
    def __init__(self):
        self.running = False
        self.services = {}
        
        # Setup logging
        setup_logging(Config.LOG_LEVEL, Config.LOG_FILE)
        logger.info("Starting Content Generation System...")
        
        # Validate configuration
        try:
            Config.validate_config()
            logger.info("Configuration validated successfully")
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)
    
    async def initialize_services(self):
        """Initialize all services"""
        try:
            # Initialize database managers
            logger.info("Initializing database connections...")
            self.services['mongodb'] = MongoDBManager()
            self.services['qdrant'] = QdrantManager()
            
            # Initialize AI services
            logger.info("Initializing AI services...")
            self.services['crew_manager'] = ContentCrewManager(
                openai_api_key=Config.OPENAI_API_KEY,
                qdrant_manager=self.services['qdrant'],
                mongodb_manager=self.services['mongodb']
            )
            
            # Initialize social media services
            logger.info("Initializing social media services...")
            self.services['social_media'] = SocialMediaService()
            self.services['image_service'] = ImageService(Config.IMAGE_FOLDER)
            
            # Initialize scheduler
            logger.info("Initializing scheduler...")
            self.services['scheduler'] = SchedulerService(
                mongodb_manager=self.services['mongodb'],
                social_media_service=self.services['social_media']
            )
            
            # Initialize MCP server
            logger.info("Initializing MCP server...")
            self.services['mcp_server'] = MCPServer(Config.MCP_HOST, Config.MCP_PORT)
            
            # Update Flask app with services
            app.mongodb_manager = self.services['mongodb']
            app.qdrant_manager = self.services['qdrant']
            app.crew_manager = self.services['crew_manager']
            app.social_media_service = self.services['social_media']
            app.scheduler_service = self.services['scheduler']
            app.mcp_server = self.services['mcp_server']
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            raise
    
    def start_background_services(self):
        """Start background services"""
        try:
            # Start scheduler
            self.services['scheduler'].start()
            logger.info("Scheduler service started")
            
            # Start MCP server
            self.services['mcp_server'].start()
            logger.info("MCP server started")
            
        except Exception as e:
            logger.error(f"Error starting background services: {e}")
            raise
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the entire system"""
        try:
            self.running = True
            
            # Initialize services
            await self.initialize_services()
            
            # Start background services
            self.start_background_services()
            
            # Setup signal handlers
            self.setup_signal_handlers()
            
            logger.info("Content Generation System started successfully")
            logger.info(f"Web interface available at http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
            logger.info(f"MCP server running on {Config.MCP_HOST}:{Config.MCP_PORT}")
            
            # Start Flask app
            app.run(
                host=Config.FLASK_HOST,
                port=Config.FLASK_PORT,
                debug=Config.FLASK_DEBUG
            )
            
        except Exception as e:
            logger.error(f"Error starting system: {e}")
            await self.shutdown()
            raise
    
    async def shutdown(self):
        """Graceful shutdown"""
        if not self.running:
            return
        
        logger.info("Shutting down Content Generation System...")
        self.running = False
        
        try:
            # Stop scheduler
            if 'scheduler' in self.services:
                self.services['scheduler'].stop()
                logger.info("Scheduler stopped")
            
            # Stop MCP server
            if 'mcp_server' in self.services:
                self.services['mcp_server'].stop()
                logger.info("MCP server stopped")
            
            logger.info("Content Generation System shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main entry point"""
    system = ContentGenerationSystem()
    
    try:
        await system.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"System error: {e}")
        sys.exit(1)
    finally:
        await system.shutdown()


if __name__ == "__main__":
    # Run the system
    asyncio.run(main())
