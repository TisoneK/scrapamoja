"""
WebSocket support for real-time failure updates.

This module provides WebSocket endpoints for real-time updates
when new failures are detected or when existing failures are updated.
"""

import asyncio
import json
from typing import Dict, Optional, Set, Type
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from src.observability.logger import get_logger

logger = get_logger("failure_websocket")


class FailureUpdateManager:
    """Manages WebSocket connections for real-time failure updates."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_count = 0
    
    async def connect(self, websocket: WebSocket, client_id: str = None) -> str:
        """
        Connect a new WebSocket client.
        
        Args:
            websocket: WebSocket connection
            client_id: Optional client ID, will generate if not provided
            
        Returns:
            Client ID for the connection
        """
        if client_id is None:
            client_id = f"client_{self.connection_count}"
            self.connection_count += 1
        
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        logger.info("websocket_connected", client_id=client_id, total_connections=len(self.active_connections))
        
        # Send welcome message
        await self.send_to_client(client_id, {
            "type": "connected",
            "message": "Connected to failure updates",
            "client_id": client_id,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        return client_id
    
    def disconnect(self, client_id: str):
        """
        Disconnect a WebSocket client.
        
        Args:
            client_id: Client ID to disconnect
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info("websocket_disconnected", client_id=client_id, total_connections=len(self.active_connections))
    
    async def send_to_client(self, client_id: str, message: dict):
        """
        Send a message to a specific client.
        
        Args:
            client_id: Client ID to send to
            message: Message to send (will be JSON serialized)
        """
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning("websocket_send_failed", client_id=client_id, error=str(e))
                # Remove dead connection
                self.disconnect(client_id)
    
    async def broadcast_failure(self, failure_data: dict, update_type: str = "new_failure"):
        """
        Broadcast a failure update to all connected clients.
        
        Args:
            failure_data: Failure information
            update_type: Type of update (new_failure, updated, resolved, etc.)
        """
        message = {
            "type": update_type,
            "data": failure_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Send to all connected clients
        dead_connections = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.warning("websocket_broadcast_failed", client_id=client_id, error=str(e))
                dead_connections.append(client_id)
        
        # Clean up dead connections
        for client_id in dead_connections:
            self.disconnect(client_id)
        
        if self.active_connections:
            logger.info("failure_broadcast", 
                       update_type=update_type, 
                       failure_id=failure_data.get("failure_id"),
                       clients_sent=len(self.active_connections))
    
    async def broadcast_approval(self, approval_data: dict):
        """
        Broadcast a selector approval event.
        
        Args:
            approval_data: Approval information
        """
        await self.broadcast_failure(approval_data, "selector_approved")
    
    async def broadcast_rejection(self, rejection_data: dict):
        """
        Broadcast a selector rejection event.
        
        Args:
            rejection_data: Rejection information
        """
        await self.broadcast_failure(rejection_data, "selector_rejected")
    
    async def broadcast_flag_update(self, flag_data: dict):
        """
        Broadcast a flag status update.
        
        Args:
            flag_data: Flag update information
        """
        await self.broadcast_failure(flag_data, "flag_updated")
    
    def get_connection_stats(self) -> dict:
        """
        Get statistics about active connections.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "active_connections": len(self.active_connections),
            "total_connections_ever": self.connection_count,
            "client_ids": list(self.active_connections.keys()),
        }


# Global instance
failure_update_manager = FailureUpdateManager()


def get_failure_update_manager() -> FailureUpdateManager:
    """Get the global failure update manager instance."""
    return failure_update_manager


# WebSocket endpoint handler
async def websocket_endpoint(websocket: WebSocket, client_id: str = None):
    """
    WebSocket endpoint for real-time failure updates.
    
    Args:
        websocket: WebSocket connection
        client_id: Optional client ID
    """
    manager = get_failure_update_manager()
    client_id = await manager.connect(websocket, client_id)
    
    try:
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client message (ping/keepalive)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle client messages (ping, subscribe, etc.)
                if message.get("type") == "ping":
                    await manager.send_to_client(client_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                elif message.get("type") == "subscribe":
                    # Client wants to subscribe to specific failure types
                    await manager.send_to_client(client_id, {
                        "type": "subscribed",
                        "filters": message.get("filters", {}),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON, send error but keep connection
                await manager.send_to_client(client_id, {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except Exception as e:
                logger.error("websocket_message_error", client_id=client_id, error=str(e))
                break
    
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(client_id)
