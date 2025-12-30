#!/usr/bin/env python3
"""
WebSocket Progress Manager
Manages WebSocket connections and broadcasts progress updates during video analysis.
"""

import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProgressManager:
    """Manages progress updates for analysis tasks."""
    
    def __init__(self):
        self.active_analyses: Dict[str, Dict] = {}
        self.connections: Dict[str, Set] = {}  # analysis_id -> set of connection IDs
    
    def register_analysis(self, analysis_id: str, total_steps: int = 7):
        """Register a new analysis task."""
        self.active_analyses[analysis_id] = {
            'progress': 0.0,
            'current_step': 0,
            'total_steps': total_steps,
            'status': 'initializing',
            'message': 'Initializing analysis...',
            'started_at': datetime.now().isoformat()
        }
        self.connections[analysis_id] = set()
        logger.info(f"Registered analysis: {analysis_id}")
    
    def update_progress(
        self,
        analysis_id: str,
        progress: float,
        status: str,
        message: str,
        step: Optional[int] = None
    ):
        """Update progress for an analysis."""
        if analysis_id not in self.active_analyses:
            self.register_analysis(analysis_id)
        
        self.active_analyses[analysis_id].update({
            'progress': min(100.0, max(0.0, progress)),
            'status': status,
            'message': message,
            'updated_at': datetime.now().isoformat()
        })
        
        if step is not None:
            self.active_analyses[analysis_id]['current_step'] = step
    
    def get_progress(self, analysis_id: str) -> Optional[Dict]:
        """Get current progress for an analysis."""
        return self.active_analyses.get(analysis_id)
    
    def complete_analysis(self, analysis_id: str, result: Dict):
        """Mark analysis as complete."""
        if analysis_id in self.active_analyses:
            self.active_analyses[analysis_id].update({
                'progress': 100.0,
                'status': 'completed',
                'message': 'Analysis complete',
                'result': result,
                'completed_at': datetime.now().isoformat()
            })
    
    def remove_analysis(self, analysis_id: str):
        """Remove analysis from tracking."""
        if analysis_id in self.active_analyses:
            del self.active_analyses[analysis_id]
        if analysis_id in self.connections:
            del self.connections[analysis_id]
    
    def add_connection(self, analysis_id: str, connection_id: str):
        """Add a WebSocket connection for an analysis."""
        if analysis_id not in self.connections:
            self.connections[analysis_id] = set()
        self.connections[analysis_id].add(connection_id)
    
    def remove_connection(self, analysis_id: str, connection_id: str):
        """Remove a WebSocket connection."""
        if analysis_id in self.connections:
            self.connections[analysis_id].discard(connection_id)
    
    def get_connections(self, analysis_id: str) -> Set[str]:
        """Get all connections for an analysis."""
        return self.connections.get(analysis_id, set())


# Global progress manager instance
progress_manager = ProgressManager()

