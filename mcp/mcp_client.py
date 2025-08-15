


# mcp/mcp_client.py
import json
import asyncio
import websockets
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP Client for connecting to the content generation server"""
    
    def __init__(self, server_url: str = "ws://localhost:8001"):
        self.server_url = server_url
        self.websocket = None
        self.request_id = 0
        self.initialized = False
    
    async def connect(self):
        """Connect to the MCP server"""
        try:
            self.websocket = await websockets.connect(self.server_url)
            await self._initialize()
            logger.info("Connected to MCP server")
        except Exception as e:
            logger.error(f"Error connecting to MCP server: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.initialized = False
            logger.info("Disconnected from MCP server")
    
    async def _initialize(self):
        """Initialize the MCP connection"""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": "Content Generation Client",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }
        
        response = await self._send_request(request)
        if response.get("result"):
            self.initialized = True
            logger.info("MCP client initialized successfully")
        else:
            raise Exception(f"Initialization failed: {response}")
    
    async def list_tools(self) -> List[Dict]:
        """List available tools"""
        if not self.initialized:
            raise Exception("Client not initialized")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/list"
        }
        
        response = await self._send_request(request)
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """Call a tool on the server"""
        if not self.initialized:
            raise Exception("Client not initialized")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = await self._send_request(request)
        return response.get("result", {})
    
    async def list_resources(self) -> List[Dict]:
        """List available resources"""
        if not self.initialized:
            raise Exception("Client not initialized")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "resources/list"
        }
        
        response = await self._send_request(request)
        return response.get("result", {}).get("resources", [])
    
    async def read_resource(self, uri: str) -> Dict:
        """Read a resource from the server"""
        if not self.initialized:
            raise Exception("Client not initialized")
        
        request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id(),
            "method": "resources/read",
            "params": {"uri": uri}
        }
        
        response = await self._send_request(request)
        return response.get("result", {})
    
    async def _send_request(self, request: Dict) -> Dict:
        """Send a request to the server and wait for response"""
        try:
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error sending request: {e}")
            raise
    
    def _next_request_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id