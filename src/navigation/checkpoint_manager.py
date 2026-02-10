"""
Navigation checkpointing and resume functionality

Provides checkpoint and resume capabilities for long-running navigation operations
with state persistence, recovery, and progress tracking.
"""

import json
import pickle
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from .models import NavigationContext, NavigationRoute
from .logging_config import get_navigation_logger


@dataclass
class NavigationCheckpoint:
    """Navigation operation checkpoint"""
    checkpoint_id: str
    operation_type: str
    timestamp: datetime
    correlation_id: str
    session_id: str
    
    # State information
    current_step: int
    total_steps: int
    completed_routes: List[str]
    failed_routes: List[str]
    pending_routes: List[str]
    
    # Context data
    navigation_context: Optional[Dict[str, Any]]
    operation_data: Dict[str, Any]
    
    # Recovery information
    recovery_point: str
    recovery_data: Dict[str, Any]


class NavigationCheckpointManager:
    """Navigation checkpoint manager"""
    
    def __init__(self, checkpoint_dir: str = "data/navigation/checkpoints"):
        """Initialize checkpoint manager"""
        self.logger = get_navigation_logger("checkpoint_manager")
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(
            "Checkpoint manager initialized",
            checkpoint_dir=str(self.checkpoint_dir)
        )
    
    def create_checkpoint(
        self,
        operation_type: str,
        correlation_id: str,
        session_id: str,
        current_step: int,
        total_steps: int,
        completed_routes: List[str],
        failed_routes: List[str],
        pending_routes: List[str],
        navigation_context: Optional[NavigationContext] = None,
        operation_data: Optional[Dict[str, Any]] = None,
        recovery_point: str = "current",
        recovery_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create navigation checkpoint"""
        try:
            checkpoint_id = f"ckpt_{operation_type}_{correlation_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
            
            checkpoint = NavigationCheckpoint(
                checkpoint_id=checkpoint_id,
                operation_type=operation_type,
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id,
                session_id=session_id,
                current_step=current_step,
                total_steps=total_steps,
                completed_routes=completed_routes,
                failed_routes=failed_routes,
                pending_routes=pending_routes,
                navigation_context=asdict(navigation_context) if navigation_context else None,
                operation_data=operation_data or {},
                recovery_point=recovery_point,
                recovery_data=recovery_data or {}
            )
            
            # Save checkpoint
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(asdict(checkpoint), f, indent=2, default=str)
            
            self.logger.info(
                "Checkpoint created",
                checkpoint_id=checkpoint_id,
                operation_type=operation_type,
                progress=f"{current_step}/{total_steps}"
            )
            
            return checkpoint_id
            
        except Exception as e:
            self.logger.error(f"Failed to create checkpoint: {str(e)}")
            raise
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[NavigationCheckpoint]:
        """Load navigation checkpoint"""
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            
            if not checkpoint_file.exists():
                return None
            
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
            
            # Convert timestamp back to datetime
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            
            checkpoint = NavigationCheckpoint(**data)
            
            self.logger.info(
                "Checkpoint loaded",
                checkpoint_id=checkpoint_id,
                operation_type=checkpoint.operation_type
            )
            
            return checkpoint
            
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {str(e)}")
            return None
    
    def list_checkpoints(
        self,
        operation_type: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 50
    ) -> List[NavigationCheckpoint]:
        """List available checkpoints"""
        try:
            checkpoints = []
            
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                try:
                    with open(checkpoint_file, 'r') as f:
                        data = json.load(f)
                    
                    data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                    checkpoint = NavigationCheckpoint(**data)
                    
                    # Apply filters
                    if operation_type and checkpoint.operation_type != operation_type:
                        continue
                    
                    if session_id and checkpoint.session_id != session_id:
                        continue
                    
                    checkpoints.append(checkpoint)
                    
                except Exception:
                    continue
            
            # Sort by timestamp (newest first) and limit
            checkpoints.sort(key=lambda c: c.timestamp, reverse=True)
            return checkpoints[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to list checkpoints: {str(e)}")
            return []
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete checkpoint"""
        try:
            checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
            
            if checkpoint_file.exists():
                checkpoint_file.unlink()
                self.logger.info("Checkpoint deleted", checkpoint_id=checkpoint_id)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to delete checkpoint: {str(e)}")
            return False
    
    def cleanup_old_checkpoints(self, days_old: int = 7) -> int:
        """Clean up old checkpoints"""
        try:
            cutoff_date = datetime.utcnow().timestamp() - (days_old * 24 * 3600)
            deleted_count = 0
            
            for checkpoint_file in self.checkpoint_dir.glob("*.json"):
                if checkpoint_file.stat().st_mtime < cutoff_date:
                    checkpoint_file.unlink()
                    deleted_count += 1
            
            self.logger.info(
                "Old checkpoints cleaned up",
                deleted_count=deleted_count,
                days_old=days_old
            )
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup checkpoints: {str(e)}")
            return 0


def create_checkpoint_manager(checkpoint_dir: str = "data/navigation/checkpoints") -> NavigationCheckpointManager:
    """Create checkpoint manager"""
    return NavigationCheckpointManager(checkpoint_dir)
