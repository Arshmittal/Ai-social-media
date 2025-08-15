# database/mongodb_manager.py
import os
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class MongoDBManager:
    def __init__(self):
        self.client = MongoClient(os.getenv('MONGODB_URI'))
        self.db = self.client.content_system
        
        # Collections
        self.projects = self.db.projects
        self.content = self.db.content
        self.schedules = self.db.schedules
        self.analytics = self.db.analytics
        
        # Create indexes
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            self.projects.create_index("name", unique=True)
            self.content.create_index("project_id")
            self.content.create_index("status")
            self.schedules.create_index("schedule_time")
            self.schedules.create_index("status")
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def create_project(self, project_data: Dict) -> str:
        """Create a new project"""
        try:
            result = self.projects.insert_one(project_data)
            logger.info(f"Project created with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating project: {e}")
            raise
    
    def get_project(self, project_id: str) -> Dict:
        """Get project by ID"""
        try:
            project = self.projects.find_one({"_id": ObjectId(project_id)})
            if project:
                project['_id'] = str(project['_id'])
            return project
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return None
    
    def get_all_projects(self) -> List[Dict]:
        """Get all projects"""
        try:
            projects = list(self.projects.find({"status": "active"}))
            for project in projects:
                project['_id'] = str(project['_id'])
            return projects
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []
    
    def update_project(self, project_id: str, updates: Dict) -> bool:
        """Update project"""
        try:
            result = self.projects.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {**updates, "updated_at": datetime.utcnow()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating project: {e}")
            return False
    
    def save_content(self, project_id: str, content_data: Dict) -> str:
        """Save generated content"""
        try:
            content_doc = {
                "project_id": ObjectId(project_id),
                "content": content_data.get('content'),
                "platform": content_data.get('platform'),
                "content_type": content_data.get('content_type'),
                "hashtags": content_data.get('hashtags', []),
                "status": "draft",
                "created_at": datetime.utcnow(),
                "metadata": content_data.get('metadata', {})
            }
            
            result = self.content.insert_one(content_doc)
            logger.info(f"Content saved with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving content: {e}")
            raise
    
    def get_content(self, content_id: str) -> Dict:
        """Get content by ID"""
        try:
            content = self.content.find_one({"_id": ObjectId(content_id)})
            if content:
                content['_id'] = str(content['_id'])
                content['project_id'] = str(content['project_id'])
            return content
        except Exception as e:
            logger.error(f"Error getting content: {e}")
            return None
    
    def get_project_content(self, project_id: str) -> List[Dict]:
        """Get all content for a project"""
        try:
            content_list = list(self.content.find({"project_id": ObjectId(project_id)}))
            for content in content_list:
                content['_id'] = str(content['_id'])
                content['project_id'] = str(content['project_id'])
            return content_list
        except Exception as e:
            logger.error(f"Error getting project content: {e}")
            return []
    
    def update_content_status(self, content_id: str, status: str, post_result: Dict = None):
        """Update content status after posting"""
        try:
            updates = {
                "status": status,
                "updated_at": datetime.utcnow()
            }
            
            if post_result:
                updates["post_result"] = post_result
                updates["posted_at"] = datetime.utcnow()
            
            self.content.update_one(
                {"_id": ObjectId(content_id)},
                {"$set": updates}
            )
            logger.info(f"Content status updated: {content_id} -> {status}")
        except Exception as e:
            logger.error(f"Error updating content status: {e}")
    
    def save_schedule(self, content_id: str, schedule_time: datetime, platform: str) -> str:
        """Save content schedule"""
        try:
            schedule_doc = {
                "content_id": ObjectId(content_id),
                "schedule_time": schedule_time,
                "platform": platform,
                "status": "pending",
                "created_at": datetime.utcnow()
            }
            
            result = self.schedules.insert_one(schedule_doc)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving schedule: {e}")
            raise
    
    def get_pending_schedules(self) -> List[Dict]:
        """Get all pending scheduled posts"""
        try:
            schedules = list(self.schedules.find({
                "status": "pending",
                "schedule_time": {"$lte": datetime.utcnow()}
            }))
            
            for schedule in schedules:
                schedule['_id'] = str(schedule['_id'])
                schedule['content_id'] = str(schedule['content_id'])
            
            return schedules
        except Exception as e:
            logger.error(f"Error getting pending schedules: {e}")
            return []
    
    def update_schedule_status(self, schedule_id: str, status: str):
        """Update schedule status"""
        try:
            self.schedules.update_one(
                {"_id": ObjectId(schedule_id)},
                {"$set": {"status": status, "executed_at": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"Error updating schedule status: {e}")
    
    def save_analytics(self, content_id: str, platform: str, metrics: Dict):
        """Save content analytics"""
        try:
            analytics_doc = {
                "content_id": ObjectId(content_id),
                "platform": platform,
                "metrics": metrics,
                "recorded_at": datetime.utcnow()
            }
            
            self.analytics.insert_one(analytics_doc)
            logger.info(f"Analytics saved for content: {content_id}")
        except Exception as e:
            logger.error(f"Error saving analytics: {e}")


