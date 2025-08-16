# services/scheduler_service.py
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import asyncio
import pytz

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self, mongodb_manager=None, social_media_service=None):
        self.mongodb_manager = mongodb_manager
        self.social_media_service = social_media_service
        self.running = False
        self.scheduler_thread = None
    
    def start(self):
        """Start the scheduler service"""
        if not self.running:
            self.running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            logger.info("Scheduler service started")
    
    def stop(self):
        """Stop the scheduler service"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logger.info("Scheduler service stopped")
    
    def _run_scheduler(self):
        """Run the scheduler in a separate thread"""
        # Schedule periodic checks every minute
        schedule.every(1).minutes.do(self._check_scheduled_posts)
        
        while self.running:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds
    
    def _check_scheduled_posts(self):
        """Check for posts that need to be published"""
        try:
            if not self.mongodb_manager:
                logger.warning("MongoDB manager not available")
                return
                
            current_utc = datetime.utcnow()
            ist = pytz.timezone('Asia/Kolkata')
            current_ist = current_utc.replace(tzinfo=pytz.UTC).astimezone(ist)
            
            logger.info(f"Checking scheduled posts at {current_utc} UTC ({current_ist.strftime('%Y-%m-%d %H:%M:%S IST')})")
                
            # Get all pending scheduled posts
            pending_schedules = self.mongodb_manager.get_pending_schedules()
            logger.info(f"Found {len(pending_schedules)} pending schedules to check")
            
            for schedule_item in pending_schedules:
                # Convert schedule time to IST for logging
                schedule_utc = schedule_item['schedule_time']
                if hasattr(schedule_utc, 'replace'):
                    schedule_ist = schedule_utc.replace(tzinfo=pytz.UTC).astimezone(ist)
                    logger.info(f"Processing schedule: {schedule_item['_id']} for content: {schedule_item['content_id']}")
                    logger.info(f"Scheduled for: {schedule_utc} UTC ({schedule_ist.strftime('%Y-%m-%d %H:%M:%S IST')})")
                
                try:
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self._execute_scheduled_post(schedule_item))
                    loop.close()
                except Exception as e:
                    logger.error(f"Error executing scheduled post {schedule_item['_id']}: {e}")
                    self.mongodb_manager.update_schedule_status(schedule_item['_id'], 'failed')
                
        except Exception as e:
            logger.error(f"Error checking scheduled posts: {e}")
    
    async def _execute_scheduled_post(self, schedule_item: Dict):
        """Execute a scheduled post"""
        try:
            logger.info(f"Executing scheduled post for content: {schedule_item['content_id']}")
            
            # Get the content to post
            content = self.mongodb_manager.get_content(schedule_item['content_id'])
            
            if not content:
                logger.error(f"Content not found for schedule: {schedule_item['_id']}")
                self.mongodb_manager.update_schedule_status(schedule_item['_id'], 'failed')
                return
            
            logger.info(f"Found content: {content.get('content', '')[:100]}...")
            
            # Post to social media
            if self.social_media_service:
                logger.info(f"Posting to {schedule_item.get('platform', 'unknown')} platform")
                result = await self.social_media_service.post_content(content)
                
                logger.info(f"Post result: {result}")
                
                if result.get('success', False):
                    # Update content status
                    self.mongodb_manager.update_content_status(
                        schedule_item['content_id'], 
                        'posted', 
                        result
                    )
                    
                    # Update schedule status
                    self.mongodb_manager.update_schedule_status(schedule_item['_id'], 'completed')
                    
                    logger.info(f"Successfully posted scheduled content: {schedule_item['content_id']}")
                else:
                    # Mark schedule as failed
                    self.mongodb_manager.update_schedule_status(schedule_item['_id'], 'failed')
                    logger.error(f"Failed to post scheduled content: {result}")
            else:
                logger.error("Social media service not available")
                self.mongodb_manager.update_schedule_status(schedule_item['_id'], 'failed')
            
        except Exception as e:
            logger.error(f"Error executing scheduled post: {e}")
            self.mongodb_manager.update_schedule_status(schedule_item['_id'], 'failed')
    
    def schedule_post(self, content_id: str, schedule_time: datetime, platform: str = None):
        """Schedule a post for future publishing"""
        try:
            if not self.mongodb_manager:
                raise Exception("MongoDB manager not configured")
            
            # Get content details
            content = self.mongodb_manager.get_content(content_id)
            if not content:
                raise Exception("Content not found")
            
            platform = platform or content.get('platform')
            
            # Save schedule to database
            schedule_id = self.mongodb_manager.save_schedule(content_id, schedule_time, platform)
            
            logger.info(f"Content scheduled: {content_id} for {schedule_time}")
            return schedule_id
            
        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            raise
    
    def get_scheduled_posts(self, project_id: str = None) -> List[Dict]:
        """Get all scheduled posts for a project or all projects"""
        try:
            if not self.mongodb_manager:
                return []
            
            # This would need to be implemented in MongoDB manager
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error(f"Error getting scheduled posts: {e}")
            return []
    
    def cancel_scheduled_post(self, schedule_id: str) -> bool:
        """Cancel a scheduled post"""
        try:
            if not self.mongodb_manager:
                return False
            
            # Update schedule status to cancelled
            self.mongodb_manager.update_schedule_status(schedule_id, 'cancelled')
            logger.info(f"Scheduled post cancelled: {schedule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling scheduled post: {e}")
            return False


