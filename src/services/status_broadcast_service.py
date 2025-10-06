#!/usr/bin/env python3
"""
Status Broadcast Service Implementation
Work Order #31 - WebSocket Status API Integration

This module handles broadcasting status updates to subscribed WebSocket clients
and manages subscription management for real-time status streaming.
"""

import logging
from typing import Dict, Any, Set, Optional
from uuid import UUID
from datetime import datetime, timezone

from src.api.status_integration import StatusTrackingResponse
from src.services.websocket_service import get_websocket_service
from src.services.redis_pubsub_service import get_redis_pubsub_service

# Configure logging
logger = logging.getLogger(__name__)

class StatusBroadcastService:
    """Service for broadcasting status updates to WebSocket clients"""
    
    def __init__(self):
        self.websocket_service = get_websocket_service()
        self.redis_pubsub = get_redis_pubsub_service()
        self.analysis_subscriptions: Dict[str, Set[str]] = {}  # analysis_id -> set of connection_ids
        self.connection_subscriptions: Dict[str, Set[str]] = {}  # connection_id -> set of analysis_ids
        self.broadcast_stats = {
            'total_broadcasts': 0,
            'successful_broadcasts': 0,
            'failed_broadcasts': 0,
            'active_subscriptions': 0
        }
    
    async def broadcast_analysis_status(self, analysis_id: str, status_response: StatusTrackingResponse):
        """
        Broadcast analysis status update to all subscribed clients
        
        Args:
            analysis_id: ID of the analysis
            status_response: Status tracking response to broadcast
        """
        try:
            self.broadcast_stats['total_broadcasts'] += 1
            
            # Get subscribed connections for this analysis
            subscribed_connections = self.get_subscribed_connections(analysis_id)
            
            if not subscribed_connections:
                logger.debug(f"No subscribed connections for analysis {analysis_id}")
                return
            
            # Prepare broadcast message
            broadcast_message = {
                'type': 'status_update',
                'analysis_id': analysis_id,
                'status': status_response.dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to each subscribed connection
            successful_broadcasts = 0
            failed_broadcasts = 0
            
            for connection_id in subscribed_connections:
                try:
                    await self._send_to_connection(connection_id, broadcast_message)
                    successful_broadcasts += 1
                except Exception as e:
                    logger.error(f"Failed to broadcast to connection {connection_id}: {e}")
                    failed_broadcasts += 1
                    # Remove failed connection from subscriptions
                    await self.unsubscribe_from_analysis(connection_id, analysis_id)
            
            # Update stats
            self.broadcast_stats['successful_broadcasts'] += successful_broadcasts
            self.broadcast_stats['failed_broadcasts'] += failed_broadcasts
            
            logger.info(f"Broadcasted status update for analysis {analysis_id} to {successful_broadcasts} connections")
            
        except Exception as e:
            logger.error(f"Error broadcasting status update for analysis {analysis_id}: {e}")
            self.broadcast_stats['failed_broadcasts'] += 1
    
    async def broadcast_stage_transition(self, analysis_id: str, stage_data: Dict[str, Any]):
        """
        Broadcast stage transition event
        
        Args:
            analysis_id: ID of the analysis
            stage_data: Stage transition data
        """
        try:
            # Get subscribed connections
            subscribed_connections = self.get_subscribed_connections(analysis_id)
            
            if not subscribed_connections:
                return
            
            # Prepare stage transition message
            transition_message = {
                'type': 'stage_transition',
                'analysis_id': analysis_id,
                'stage_data': stage_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to subscribed connections
            for connection_id in subscribed_connections:
                try:
                    await self._send_to_connection(connection_id, transition_message)
                except Exception as e:
                    logger.error(f"Failed to broadcast stage transition to connection {connection_id}: {e}")
                    await self.unsubscribe_from_analysis(connection_id, analysis_id)
            
            logger.debug(f"Broadcasted stage transition for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting stage transition for analysis {analysis_id}: {e}")
    
    async def broadcast_progress_update(self, analysis_id: str, progress_data: Dict[str, Any]):
        """
        Broadcast progress update event
        
        Args:
            analysis_id: ID of the analysis
            progress_data: Progress update data
        """
        try:
            # Get subscribed connections
            subscribed_connections = self.get_subscribed_connections(analysis_id)
            
            if not subscribed_connections:
                return
            
            # Prepare progress update message
            progress_message = {
                'type': 'progress_update',
                'analysis_id': analysis_id,
                'progress_data': progress_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to subscribed connections
            for connection_id in subscribed_connections:
                try:
                    await self._send_to_connection(connection_id, progress_message)
                except Exception as e:
                    logger.error(f"Failed to broadcast progress update to connection {connection_id}: {e}")
                    await self.unsubscribe_from_analysis(connection_id, analysis_id)
            
            logger.debug(f"Broadcasted progress update for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting progress update for analysis {analysis_id}: {e}")
    
    async def broadcast_error_update(self, analysis_id: str, error_data: Dict[str, Any]):
        """
        Broadcast error update event
        
        Args:
            analysis_id: ID of the analysis
            error_data: Error data
        """
        try:
            # Get subscribed connections
            subscribed_connections = self.get_subscribed_connections(analysis_id)
            
            if not subscribed_connections:
                return
            
            # Prepare error update message
            error_message = {
                'type': 'error_update',
                'analysis_id': analysis_id,
                'error_data': error_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to subscribed connections
            for connection_id in subscribed_connections:
                try:
                    await self._send_to_connection(connection_id, error_message)
                except Exception as e:
                    logger.error(f"Failed to broadcast error update to connection {connection_id}: {e}")
                    await self.unsubscribe_from_analysis(connection_id, analysis_id)
            
            logger.debug(f"Broadcasted error update for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting error update for analysis {analysis_id}: {e}")
    
    async def broadcast_completion_update(self, analysis_id: str, completion_data: Dict[str, Any]):
        """
        Broadcast completion update event
        
        Args:
            analysis_id: ID of the analysis
            completion_data: Completion data
        """
        try:
            # Get subscribed connections
            subscribed_connections = self.get_subscribed_connections(analysis_id)
            
            if not subscribed_connections:
                return
            
            # Prepare completion update message
            completion_message = {
                'type': 'completion_update',
                'analysis_id': analysis_id,
                'completion_data': completion_data,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to subscribed connections
            for connection_id in subscribed_connections:
                try:
                    await self._send_to_connection(connection_id, completion_message)
                except Exception as e:
                    logger.error(f"Failed to broadcast completion update to connection {connection_id}: {e}")
                    await self.unsubscribe_from_analysis(connection_id, analysis_id)
            
            logger.debug(f"Broadcasted completion update for analysis {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting completion update for analysis {analysis_id}: {e}")
    
    async def subscribe_to_analysis(self, connection_id: str, analysis_id: str) -> bool:
        """
        Subscribe a connection to analysis updates
        
        Args:
            connection_id: ID of the WebSocket connection
            analysis_id: ID of the analysis
            
        Returns:
            True if subscription successful, False otherwise
        """
        try:
            # Add to analysis subscriptions
            if analysis_id not in self.analysis_subscriptions:
                self.analysis_subscriptions[analysis_id] = set()
            self.analysis_subscriptions[analysis_id].add(connection_id)
            
            # Add to connection subscriptions
            if connection_id not in self.connection_subscriptions:
                self.connection_subscriptions[connection_id] = set()
            self.connection_subscriptions[connection_id].add(analysis_id)
            
            # Update stats
            self.broadcast_stats['active_subscriptions'] = len(self.connection_subscriptions)
            
            logger.info(f"Connection {connection_id} subscribed to analysis {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing connection {connection_id} to analysis {analysis_id}: {e}")
            return False
    
    async def unsubscribe_from_analysis(self, connection_id: str, analysis_id: str) -> bool:
        """
        Unsubscribe a connection from analysis updates
        
        Args:
            connection_id: ID of the WebSocket connection
            analysis_id: ID of the analysis
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        try:
            # Remove from analysis subscriptions
            if analysis_id in self.analysis_subscriptions:
                self.analysis_subscriptions[analysis_id].discard(connection_id)
                if not self.analysis_subscriptions[analysis_id]:
                    del self.analysis_subscriptions[analysis_id]
            
            # Remove from connection subscriptions
            if connection_id in self.connection_subscriptions:
                self.connection_subscriptions[connection_id].discard(analysis_id)
                if not self.connection_subscriptions[connection_id]:
                    del self.connection_subscriptions[connection_id]
            
            # Update stats
            self.broadcast_stats['active_subscriptions'] = len(self.connection_subscriptions)
            
            logger.info(f"Connection {connection_id} unsubscribed from analysis {analysis_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing connection {connection_id} from analysis {analysis_id}: {e}")
            return False
    
    async def unsubscribe_all_connections(self, connection_id: str) -> bool:
        """
        Unsubscribe a connection from all analysis updates
        
        Args:
            connection_id: ID of the WebSocket connection
            
        Returns:
            True if unsubscription successful, False otherwise
        """
        try:
            # Get all subscribed analyses for this connection
            subscribed_analyses = self.connection_subscriptions.get(connection_id, set()).copy()
            
            # Unsubscribe from each analysis
            for analysis_id in subscribed_analyses:
                await self.unsubscribe_from_analysis(connection_id, analysis_id)
            
            logger.info(f"Connection {connection_id} unsubscribed from all analyses")
            return True
            
        except Exception as e:
            logger.error(f"Error unsubscribing connection {connection_id} from all analyses: {e}")
            return False
    
    def get_subscribed_connections(self, analysis_id: str) -> Set[str]:
        """
        Get all connections subscribed to an analysis
        
        Args:
            analysis_id: ID of the analysis
            
        Returns:
            Set of connection IDs
        """
        return self.analysis_subscriptions.get(analysis_id, set()).copy()
    
    def get_connection_subscriptions(self, connection_id: str) -> Set[str]:
        """
        Get all analyses a connection is subscribed to
        
        Args:
            connection_id: ID of the connection
            
        Returns:
            Set of analysis IDs
        """
        return self.connection_subscriptions.get(connection_id, set()).copy()
    
    async def cleanup_stale_connections(self):
        """Clean up stale connections and their subscriptions"""
        try:
            # This would typically check with the WebSocket service for active connections
            # For now, we'll implement a simple cleanup based on connection tracking
            
            stale_connections = []
            
            # Check each connection subscription
            for connection_id in list(self.connection_subscriptions.keys()):
                # Check if connection is still active (this would typically check with WebSocket service)
                # For now, we'll assume all connections are active unless explicitly marked as stale
                pass
            
            # Remove stale connections
            for connection_id in stale_connections:
                await self.unsubscribe_all_connections(connection_id)
            
            if stale_connections:
                logger.info(f"Cleaned up {len(stale_connections)} stale connections")
            
        except Exception as e:
            logger.error(f"Error cleaning up stale connections: {e}")
    
    async def _send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """Send message to a specific connection"""
        try:
            # Import here to avoid circular imports
            from src.api.websocket_status_api import websocket_status_api
            
            # Get connection info
            connection_info = websocket_status_api.active_connections.get(connection_id)
            if not connection_info:
                raise Exception(f"Connection {connection_id} not found")
            
            websocket = connection_info['websocket']
            
            # Send message
            import json
            await websocket.send_text(json.dumps(message))
            
        except Exception as e:
            logger.error(f"Error sending message to connection {connection_id}: {e}")
            raise
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        return {
            'total_analyses_tracked': len(self.analysis_subscriptions),
            'total_connections_subscribed': len(self.connection_subscriptions),
            'broadcast_stats': self.broadcast_stats.copy(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_active_analyses(self) -> Set[str]:
        """Get set of all active analyses being tracked"""
        return set(self.analysis_subscriptions.keys())
    
    def get_active_connections(self) -> Set[str]:
        """Get set of all active connections"""
        return set(self.connection_subscriptions.keys())

# Global instance
status_broadcast_service = StatusBroadcastService()
