# mcp/mcp_server.py
import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class MCPServer:
    """Model Context Protocol Server for content generation system"""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.running = False
        self.clients = {}
        self.tools = {}
        self.resources = {}
        self._setup_default_tools()
    
    def _setup_default_tools(self):
        """Setup default MCP tools"""
        self.tools = {
            "get_project_info": {
                "description": "Get information about a specific project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "The project ID to get information for"
                        }
                    },
                    "required": ["project_id"]
                }
            },
            "generate_content": {
                "description": "Generate content for a project and platform",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "topic": {"type": "string"},
                        "platform": {"type": "string"},
                        "content_type": {"type": "string"},
                        "include_media": {"type": "boolean"}
                    },
                    "required": ["project_id", "topic", "platform"]
                }
            },
            "schedule_content": {
                "description": "Schedule content for posting",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content_id": {"type": "string"},
                        "schedule_time": {"type": "string"},
                        "platform": {"type": "string"}
                    },
                    "required": ["content_id", "schedule_time"]
                }
            },
            "get_analytics": {
                "description": "Get analytics for posted content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "platform": {"type": "string"},
                        "date_range": {"type": "string"}
                    },
                    "required": ["project_id"]
                }
            },
            "search_similar_content": {
                "description": "Search for similar content using vector similarity",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string"},
                        "query": {"type": "string"},
                        "limit": {"type": "integer"}
                    },
                    "required": ["project_id", "query"]
                }
            }
        }
        
        self.resources = {
            "projects": {
                "description": "Available projects in the system",
                "uri": "content://projects",
                "mimeType": "application/json"
            },
            "templates": {
                "description": "Content templates for different platforms",
                "uri": "content://templates",
                "mimeType": "application/json"
            },
            "analytics": {
                "description": "System analytics and performance data",
                "uri": "content://analytics",
                "mimeType": "application/json"
            }
        }
    
    def start(self):
        """Start the MCP server"""
        try:
            self.running = True
            logger.info(f"MCP Server started on {self.host}:{self.port}")
            # In a real implementation, this would start an actual server
            # For now, we'll just mark it as running
        except Exception as e:
            logger.error(f"Error starting MCP server: {e}")
    
    def stop(self):
        """Stop the MCP server"""
        self.running = False
        logger.info("MCP Server stopped")
    
    async def handle_request(self, client_id: str, request: Dict) -> Dict:
        """Handle MCP requests from clients"""
        try:
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            if method == "initialize":
                return await self._handle_initialize(client_id, params, request_id)
            elif method == "tools/list":
                return await self._handle_list_tools(request_id)
            elif method == "tools/call":
                return await self._handle_tool_call(params, request_id)
            elif method == "resources/list":
                return await self._handle_list_resources(request_id)
            elif method == "resources/read":
                return await self._handle_read_resource(params, request_id)
            else:
                return self._error_response(request_id, f"Unknown method: {method}")
                
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return self._error_response(request.get("id"), str(e))
    
    async def _handle_initialize(self, client_id: str, params: Dict, request_id: str) -> Dict:
        """Handle client initialization"""
        try:
            client_info = {
                "name": params.get("clientInfo", {}).get("name", "unknown"),
                "version": params.get("clientInfo", {}).get("version", "unknown"),
                "connected_at": datetime.utcnow().isoformat()
            }
            
            self.clients[client_id] = client_info
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"subscribe": True, "listChanged": True}
                    },
                    "serverInfo": {
                        "name": "Content Generation MCP Server",
                        "version": "1.0.0"
                    }
                }
            }
            
        except Exception as e:
            return self._error_response(request_id, f"Initialization error: {e}")
    
    async def _handle_list_tools(self, request_id: str) -> Dict:
        """Handle tools list request"""
        try:
            tools_list = []
            for tool_name, tool_info in self.tools.items():
                tools_list.append({
                    "name": tool_name,
                    "description": tool_info["description"],
                    "inputSchema": tool_info["parameters"]
                })
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": tools_list}
            }
            
        except Exception as e:
            return self._error_response(request_id, f"Error listing tools: {e}")
    
    async def _handle_tool_call(self, params: Dict, request_id: str) -> Dict:
        """Handle tool call request"""
        try:
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name not in self.tools:
                return self._error_response(request_id, f"Unknown tool: {tool_name}")
            
            # Route tool calls to appropriate handlers
            if tool_name == "get_project_info":
                result = await self._tool_get_project_info(arguments)
            elif tool_name == "generate_content":
                result = await self._tool_generate_content(arguments)
            elif tool_name == "schedule_content":
                result = await self._tool_schedule_content(arguments)
            elif tool_name == "get_analytics":
                result = await self._tool_get_analytics(arguments)
            elif tool_name == "search_similar_content":
                result = await self._tool_search_similar_content(arguments)
            else:
                result = {"error": f"Tool {tool_name} not implemented"}
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
            
        except Exception as e:
            return self._error_response(request_id, f"Tool call error: {e}")
    
    async def _handle_list_resources(self, request_id: str) -> Dict:
        """Handle resources list request"""
        try:
            resources_list = []
            for resource_name, resource_info in self.resources.items():
                resources_list.append({
                    "uri": resource_info["uri"],
                    "name": resource_name,
                    "description": resource_info["description"],
                    "mimeType": resource_info["mimeType"]
                })
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"resources": resources_list}
            }
            
        except Exception as e:
            return self._error_response(request_id, f"Error listing resources: {e}")
    
    async def _handle_read_resource(self, params: Dict, request_id: str) -> Dict:
        """Handle resource read request"""
        try:
            uri = params.get("uri")
            
            if uri == "content://projects":
                content = await self._get_projects_resource()
            elif uri == "content://templates":
                content = await self._get_templates_resource()
            elif uri == "content://analytics":
                content = await self._get_analytics_resource()
            else:
                return self._error_response(request_id, f"Unknown resource URI: {uri}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps(content, indent=2)
                        }
                    ]
                }
            }
            
        except Exception as e:
            return self._error_response(request_id, f"Error reading resource: {e}")
    
    # Tool implementations
    async def _tool_get_project_info(self, args: Dict) -> Dict:
        """Get project information tool"""
        try:
            project_id = args.get("project_id")
            # This would integrate with your MongoDB manager
            return {
                "project_id": project_id,
                "info": "Project information would be retrieved from database",
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_generate_content(self, args: Dict) -> Dict:
        """Generate content tool"""
        try:
            project_id = args.get("project_id")
            topic = args.get("topic")
            platform = args.get("platform")
            content_type = args.get("content_type", "post")
            include_media = args.get("include_media", False)
            
            # Platform-specific character limits
            platform_limits = {
                'twitter': {'post': 280, 'thread': 280, 'poll': 220},
                'linkedin': {'post': 3000, 'article': 8000, 'poll': 2800},
                'facebook': {'post': 2000, 'story': 500, 'poll': 1800},
                'instagram': {'post': 2200, 'story': 200, 'reel': 1000}
            }
            
            char_limit = platform_limits.get(platform, {}).get(content_type, 280)
            media_suggestion = " [Include relevant visual]" if include_media else ""
            
            # Generate content based on platform and type
            if platform == 'twitter' and content_type == 'thread':
                content = f"1/3 🧵 {topic} - exploring key insights{media_suggestion}\n\n2/3 Important points about {topic} everyone should know\n\n3/3 What's your experience with {topic}? Share below! #discussion"
            elif content_type == 'poll':
                content = f"What's your take on {topic}?{media_suggestion}\n\n• Very important\n• Somewhat important\n• Not important\n• Need more info\n\nShare your thoughts! #poll"
            else:
                content = f"Exploring {topic} - key insights and takeaways{media_suggestion} #content #discussion"
            
            # Ensure content respects character limits
            if len(content) > char_limit:
                content = content[:char_limit-3] + "..."
            
            return {
                "project_id": project_id,
                "topic": topic,
                "platform": platform,
                "content_type": content_type,
                "generated_content": content,
                "character_count": len(content),
                "character_limit": char_limit,
                "include_media": include_media,
                "status": "success",
                "content_id": f"content_{datetime.utcnow().timestamp()}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_schedule_content(self, args: Dict) -> Dict:
        """Schedule content tool"""
        try:
            content_id = args.get("content_id")
            schedule_time = args.get("schedule_time")
            platform = args.get("platform")
            
            # This would integrate with your scheduler service
            return {
                "content_id": content_id,
                "scheduled_for": schedule_time,
                "platform": platform,
                "status": "scheduled",
                "schedule_id": f"schedule_{datetime.utcnow().timestamp()}"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_get_analytics(self, args: Dict) -> Dict:
        """Get analytics tool"""
        try:
            project_id = args.get("project_id")
            platform = args.get("platform")
            date_range = args.get("date_range")
            
            # This would integrate with your analytics system
            return {
                "project_id": project_id,
                "platform": platform,
                "date_range": date_range,
                "metrics": {
                    "total_posts": 10,
                    "total_engagement": 250,
                    "avg_engagement_rate": 25.0
                },
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def _tool_search_similar_content(self, args: Dict) -> Dict:
        """Search similar content tool"""
        try:
            project_id = args.get("project_id")
            query = args.get("query")
            limit = args.get("limit", 5)
            
            # This would integrate with your Qdrant vector search
            return {
                "project_id": project_id,
                "query": query,
                "results": [
                    {
                        "content": f"Similar content {i+1} for query: {query}",
                        "similarity_score": 0.9 - (i * 0.1),
                        "platform": "twitter"
                    }
                    for i in range(min(limit, 3))
                ],
                "status": "success"
            }
        except Exception as e:
            return {"error": str(e)}
    
    # Resource implementations
    async def _get_projects_resource(self) -> Dict:
        """Get projects resource"""
        return {
            "projects": [
                {
                    "id": "project_1",
                    "name": "Sample Project 1",
                    "status": "active",
                    "platforms": ["twitter", "linkedin"]
                },
                {
                    "id": "project_2",
                    "name": "Sample Project 2",
                    "status": "active",
                    "platforms": ["facebook", "instagram"]
                }
            ],
            "total_count": 2,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def _get_templates_resource(self) -> Dict:
        """Get templates resource"""
        return {
            "templates": {
                "twitter": {
                    "post": "🔥 {topic} \n\n{content}\n\n{hashtags}",
                    "thread": "{content}\n\n{hashtags}\n\n🧵 Thread 1/{total}"
                },
                "linkedin": {
                    "post": "{content}\n\n{hashtags}\n\n#linkedin #professional"
                },
                "facebook": {
                    "post": "{content}\n\n{hashtags}"
                },
                "instagram": {
                    "post": "{content}\n\n{hashtags}\n\n📸"
                }
            },
            "last_updated": datetime.utcnow().isoformat()
        }
    
    async def _get_analytics_resource(self) -> Dict:
        """Get analytics resource"""
        return {
            "system_analytics": {
                "total_projects": 5,
                "total_content_generated": 150,
                "total_posts_published": 120,
                "success_rate": 95.5,
                "platforms": {
                    "twitter": 45,
                    "linkedin": 35,
                    "facebook": 25,
                    "instagram": 15
                }
            },
            "performance_metrics": {
                "avg_engagement_rate": 3.2,
                "top_performing_platform": "linkedin",
                "content_generation_time_avg": 45.0
            },
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _error_response(self, request_id: str, message: str) -> Dict:
        """Generate error response"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -1,
                "message": message
            }
        }
    
    def register_tool(self, name: str, description: str, parameters: Dict, handler):
        """Register a custom tool"""
        self.tools[name] = {
            "description": description,
            "parameters": parameters,
            "handler": handler
        }
        logger.info(f"Registered custom tool: {name}")
    
    def register_resource(self, name: str, uri: str, description: str, mime_type: str, handler):
        """Register a custom resource"""
        self.resources[name] = {
            "uri": uri,
            "description": description,
            "mimeType": mime_type,
            "handler": handler
        }
        logger.info(f"Registered custom resource: {name}")