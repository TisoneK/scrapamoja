"""
WebSocket client for failure notifications.

This module provides the WebSocketClient class that handles:
- Connection establishment with configurable endpoint (AC1)
- Exponential backoff reconnection logic (AC4)
- Message deduplication via unique IDs (AC5)
- Buffering failures during disconnection (Task 3)
- Real-time message dispatch (Task 2)

Story 5-1: WebSocket Connection for Failure Notifications
- AC1: WebSocket Connection Establishment
- AC2: Failure Notification Sending
- AC3: Real-Time Streaming
- AC4: Automatic Reconnection
- AC5: No Duplicate Notifications
"""

import asyncio
import logging
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Deque, List, Optional

import uuid

from src.selectors.websocket.config import WebSocketConfig
from src.selectors.websocket.models import (
    ConnectionStatus,
    FailureNotification,
    ConfidenceScoreUpdate,
    AlertNotification,
    ConfidenceScoreRefresh,
    HealthStatus,
    HealthStatusUpdate,
    SelectorHealthStatus,
    HealthSnapshot,
    BlastRadiusUpdate,
    BlastRadiusSeverity,
)


class WebSocketClientError(Exception):
    """Base exception for WebSocket client errors."""
    pass


class ConnectionError(WebSocketClientError):
    """Exception raised when WebSocket connection fails."""
    pass


class SendError(WebSocketClientError):
    """Exception raised when sending a message fails."""
    pass


class BufferOverflowError(WebSocketClientError):
    """Exception raised when buffer exceeds max size."""
    pass


class WebSocketClient:
    """
    Async WebSocket client for sending failure notifications.
    
    This client provides:
    - AC1: Connection establishment with configurable endpoint
    - AC2: Failure notification sending with JSON format
    - AC3: Real-time streaming with minimal latency
    - AC4: Automatic reconnection with exponential backoff
    - AC5: No duplicate notifications via unique message IDs
    
    Attributes:
        config: WebSocket configuration
        connected: Whether the client is currently connected
        buffer: Local buffer for failures during disconnection
    """
    
    def __init__(
        self,
        config: WebSocketConfig,
        logger: Optional[logging.Logger] = None,
        on_status_change: Optional[Callable[[ConnectionStatus], None]] = None,
    ) -> None:
        """
        Initialize the WebSocket client.
        
        Args:
            config: WebSocket configuration
            logger: Optional logger instance
            on_status_change: Optional callback for connection status changes
        """
        self.config = config
        self._logger = logger or logging.getLogger(__name__)
        self._on_status_change = on_status_change
        
        self._websocket = None
        self._connection_lock = asyncio.Lock()
        self._send_lock = asyncio.Lock()
        self._running = False
        self._retry_count = 0
        self._connected = False
        self._background_task: Optional[asyncio.Task] = None  # For background task management
        
        # Buffer for failures during disconnection (Task 3)
        self._buffer: Deque[FailureNotification] = deque(
            maxlen=config.buffer_size
        )
        
        # Track sent message IDs for deduplication (AC5)
        self._sent_message_ids: List[str] = []  # Ordered list for FIFO cleanup
        self._max_tracked_ids = 10000  # Limit memory usage
        
        # AC3: Track latency for monitoring <100ms target
        self._notification_latencies: Deque[float] = deque(maxlen=100)
    
    @property
    def connected(self) -> bool:
        """Check if the client is currently connected."""
        return self._connected
    
    @property
    def buffer_size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)
    
    @property
    def average_latency_ms(self) -> Optional[float]:
        """Get average notification latency in milliseconds (AC3)."""
        if not self._notification_latencies:
            return None
        return sum(self._notification_latencies) / len(self._notification_latencies)
    
    @property
    def max_latency_ms(self) -> Optional[float]:
        """Get maximum notification latency in milliseconds (AC3)."""
        if not self._notification_latencies:
            return None
        return max(self._notification_latencies)
    
    def _notify_status_change(self, status: str, error: Optional[str] = None) -> None:
        """Notify status change callback."""
        if self._on_status_change:
            status_obj = ConnectionStatus(
                status=status,
                timestamp=datetime.now(timezone.utc),
                retry_count=self._retry_count if status == "reconnecting" else None,
                last_error=error,
            )
            self._on_status_change(status_obj)
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection (AC1).
        
        Returns:
            True if connection successful, False otherwise
        """
        async with self._connection_lock:
            if self._connected and self._websocket:
                return True
            
            self._notify_status_change("reconnecting")
            
            try:
                # Try to import websockets library
                try:
                    import websockets
                    ws_class = websockets
                except ImportError:
                    self._logger.warning(
                        "websockets library not available, using aiohttp"
                    )
                    import aiohttp
                    ws_class = aiohttp
                
                # Connect to WebSocket endpoint
                self._logger.info(
                    f"Connecting to WebSocket: {self.config.url}"
                )
                
                if hasattr(ws_class, 'connect'):
                    # Using websockets library
                    self._websocket = await ws_class.connect(
                        self.config.url,
                        protocols=self.config.protocols,
                        extra_headers=self.config.headers,
                        ping_interval=self.config.ping_interval,
                    )
                else:
                    # Using aiohttp
                    self._websocket = await ws_class.ClientSession().ws_connect(
                        self.config.url,
                        protocols=self.config.protocols,
                        headers=self.config.headers,
                    )
                
                self._connected = True
                self._retry_count = 0
                self._notify_status_change("connected")
                self._logger.info(
                    f"WebSocket connected to: {self.config.url}"
                )
                
                # Flush buffer on successful connection (Task 3.2)
                await self._flush_buffer()
                
                # Also flush score buffer on reconnection
                await self._flush_score_buffer()
                
                # Also flush health buffer on reconnection
                await self._flush_health_buffer()
                
                return True
                
            except Exception as e:
                self._connected = False
                error_msg = f"Failed to connect: {str(e)}"
                self._logger.error(error_msg)
                self._notify_status_change("disconnected", error_msg)
                return False
    
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        async with self._connection_lock:
            if self._websocket:
                try:
                    await self._websocket.close()
                except Exception as e:
                    self._logger.warning(f"Error closing WebSocket: {e}")
                finally:
                    self._websocket = None
            self._connected = False
            self._notify_status_change("disconnected")
    
    async def _attempt_reconnect(self) -> bool:
        """
        Attempt to reconnect with exponential backoff (AC4).
        
        Returns:
            True if reconnection successful, False otherwise
        """
        if self._retry_count >= self.config.max_retries:
            self._logger.error(
                f"Max retries ({self.config.max_retries}) reached"
            )
            return False
        
        delay = self.config.calculate_backoff_delay(self._retry_count)
        self._retry_count += 1
        
        self._logger.info(
            f"Reconnecting in {delay:.2f}s (attempt {self._retry_count}/"
            f"{self.config.max_retries})"
        )
        self._notify_status_change("reconnecting")
        
        await asyncio.sleep(delay)
        
        return await self.connect()
    
    async def send_notification(
        self,
        notification: FailureNotification,
    ) -> bool:
        """
        Send failure notification via WebSocket (AC2, AC3).
        
        If not connected, the notification will be buffered.
        
        Args:
            notification: The failure notification to send
            
        Returns:
            True if sent or buffered successfully, False otherwise
        """
        # Check for duplicate (AC5)
        if notification.message_id in self._sent_message_ids:
            self._logger.debug(
                f"Duplicate notification skipped: {notification.message_id}"
            )
            return True
        
        # Try to send if connected
        if self._connected and self._websocket:
            return await self._send_message(notification)
        
        # Not connected - buffer the message (Task 3.1)
        return await self._buffer_notification(notification)
    
    async def _send_message(
        self,
        notification: FailureNotification,
    ) -> bool:
        """
        Send a single message via WebSocket.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if sent successfully
        """
        async with self._send_lock:
            try:
                message_json = notification.to_json()
                
                # AC3: Track latency for <100ms target monitoring
                send_start = datetime.now(timezone.utc)
                
                # Send with timeout (AC3: minimal latency)
                await asyncio.wait_for(
                    self._websocket.send(message_json),
                    timeout=self.config.message_timeout
                )
                
                # Calculate and record latency (AC3)
                latency_ms = (datetime.now(timezone.utc) - send_start).total_seconds() * 1000
                self._notification_latencies.append(latency_ms)
                if latency_ms > 100:
                    self._logger.warning(
                        f"Notification latency {latency_ms:.2f}ms exceeds 100ms target"
                    )
                
                # Track message ID for deduplication (AC5)
                self._sent_message_ids.append(notification.message_id)
                self._cleanup_sent_ids()
                
                self._logger.debug(
                    f"Notification sent: {notification.message_id}"
                )
                return True
                
            except asyncio.TimeoutError:
                self._logger.warning(
                    f"Message send timeout: {notification.message_id}"
                )
                # Buffer for retry
                return await self._buffer_notification(notification)
            except Exception as e:
                self._logger.error(
                    f"Failed to send notification: {e}"
                )
                # Try to reconnect
                self._connected = False
                if await self._attempt_reconnect():
                    return await self._send_message(notification)
                # Buffer for later
                return await self._buffer_notification(notification)
    
    async def send_binary(
        self,
        data: bytes,
    ) -> bool:
        """
        Send binary data via WebSocket (AC1: binary message support).
        
        Args:
            data: Binary data to send
            
        Returns:
            True if sent successfully
        """
        if not self._connected or not self._websocket:
            return False
        
        try:
            await asyncio.wait_for(
                self._websocket.send(data),
                timeout=self.config.message_timeout
            )
            return True
        except Exception as e:
            self._logger.error(f"Failed to send binary data: {e}")
            return False
    
    async def _buffer_notification(
        self,
        notification: FailureNotification,
    ) -> bool:
        """
        Buffer notification for later delivery (Task 3.1).
        
        Args:
            notification: The notification to buffer
            
        Returns:
            True if buffered successfully
        """
        if len(self._buffer) >= self.config.buffer_size:
            self._logger.warning(
                f"Buffer overflow, dropping oldest notification"
            )
            # Remove oldest to make room
            try:
                self._buffer.popleft()
            except IndexError:
                pass
        
        self._buffer.append(notification)
        self._logger.debug(
            f"Notification buffered (buffer size: {len(self._buffer)})"
        )
        return True
    
    async def _flush_buffer(self) -> None:
        """
        Flush buffered messages on reconnection (Task 3.2).
        
        Sends all buffered notifications in order.
        """
        if not self._buffer:
            return
        
        self._logger.info(
            f"Flushing {len(self._buffer)} buffered notifications"
        )
        
        # Create a copy and clear the buffer
        messages_to_send = list(self._buffer)
        self._buffer.clear()
        
        # Send each message
        for notification in messages_to_send:
            # Check if already sent (avoid duplicates)
            if notification.message_id not in self._sent_message_ids:
                await self._send_message(notification)
            else:
                self._logger.debug(
                    f"Skipping duplicate from buffer: "
                    f"{notification.message_id}"
                )
        
        self._logger.info("Buffer flush completed")
    
    def _cleanup_sent_ids(self) -> None:
        """
        Clean up old sent message IDs to prevent memory bloat (AC5).
        Uses FIFO ordering to remove oldest entries first.
        """
        if len(self._sent_message_ids) > self._max_tracked_ids:
            # Remove oldest half (FIFO - remove from front)
            ids_to_remove = len(self._sent_message_ids) - (
                self._max_tracked_ids // 2
            )
            for _ in range(ids_to_remove):
                try:
                    self._sent_message_ids.pop(0)  # Remove from front (oldest)
                except IndexError:
                    break
    
    async def send_failure(
        self,
        selector_id: str,
        page_url: str,
        failure_type: str,
        extractor_id: str,
        error_message: Optional[str] = None,
        confidence_score: Optional[float] = None,
    ) -> bool:
        """
        Convenience method to create and send a failure notification.
        
        Args:
            selector_id: ID/name of the failed selector
            page_url: URL of the page being extracted
            failure_type: Type of failure
            extractor_id: ID of the extractor running the selector
            error_message: Optional error message
            confidence_score: Optional confidence score
            
        Returns:
            True if sent or buffered successfully
        """
        notification = FailureNotification.from_failure_event(
            selector_id=selector_id,
            page_url=page_url,
            failure_type=failure_type,
            extractor_id=extractor_id,
            error_message=error_message,
            confidence_score=confidence_score,
        )
        
        return await self.send_notification(notification)
    
    async def send_confidence_score_update(
        self,
        selector_id: str,
        old_score: float,
        new_score: float,
        reason: str,
        is_threshold_breach: bool = False,
    ) -> bool:
        """
        Send confidence score update notification (AC1).
        
        When a selector's confidence score changes in the adaptive module,
        this sends a notification with the score change details.
        
        Args:
            selector_id: ID/name of the selector
            old_score: Previous confidence score (0.0-1.0)
            new_score: New confidence score (0.0-1.0)
            reason: Reason for score change (failure_detected, success_accumulated, manual_adjustment)
            is_threshold_breach: Whether this update breached a threshold
            
        Returns:
            True if sent or buffered successfully
        """
        notification = ConfidenceScoreUpdate(
            selector_id=selector_id,
            old_score=old_score,
            new_score=new_score,
            reason=reason,
            is_threshold_breach=is_threshold_breach,
        )
        
        return await self._send_score_notification(notification)
    
    async def send_alert(
        self,
        selector_id: str,
        alert_level: str,
        message: str,
        current_score: float,
        threshold: float,
    ) -> bool:
        """
        Send threshold alert notification (AC3).
        
        When a selector's confidence score drops below a configurable threshold,
        this sends an elevated priority alert.
        
        Args:
            selector_id: ID/name of the selector
            alert_level: Alert severity level (warning, critical)
            message: Human-readable alert message
            current_score: Current confidence score
            threshold: Threshold that was breached
            
        Returns:
            True if sent or buffered successfully
        """
        notification = AlertNotification(
            alert_level=alert_level,
            selector_id=selector_id,
            message=message,
            current_score=current_score,
            threshold=threshold,
        )
        
        return await self._send_score_notification(notification)
    
    async def send_confidence_refresh(
        self,
        scores: list[dict],
        is_delta: bool = False,
    ) -> bool:
        """
        Send periodic confidence score refresh broadcast (AC2).
        
        Periodically broadcasts updated scores to all connected WebSocket clients.
        
        Args:
            scores: List of selector confidence scores
            is_delta: Whether this is a delta update (vs full refresh)
            
        Returns:
            True if sent or buffered successfully
        """
        notification = ConfidenceScoreRefresh(
            scores=scores,
            is_delta=is_delta,
        )
        
        return await self._send_score_notification(notification)
    
    async def _send_score_notification(
        self,
        notification: ConfidenceScoreUpdate | AlertNotification | ConfidenceScoreRefresh,
    ) -> bool:
        """
        Internal method to send score-related notifications.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if sent or buffered successfully
        """
        # Check for duplicate
        if notification.message_id in self._sent_message_ids:
            self._logger.debug(
                f"Duplicate notification skipped: {notification.message_id}"
            )
            return True
        
        # Try to send if connected
        if self._connected and self._websocket:
            return await self._send_message_internal(notification)
        
        # Not connected - buffer the message
        return await self._buffer_score_notification(notification)
    
    async def _send_message_internal(
        self,
        notification: ConfidenceScoreUpdate | AlertNotification | ConfidenceScoreRefresh,
    ) -> bool:
        """
        Send a score notification via WebSocket.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if sent successfully
        """
        async with self._send_lock:
            try:
                message_json = notification.to_json()
                
                # Track latency
                send_start = datetime.now(timezone.utc)
                
                await asyncio.wait_for(
                    self._websocket.send(message_json),
                    timeout=self.config.message_timeout
                )
                
                # Calculate and record latency
                latency_ms = (datetime.now(timezone.utc) - send_start).total_seconds() * 1000
                self._notification_latencies.append(latency_ms)
                if latency_ms > 100:
                    self._logger.warning(
                        f"Notification latency {latency_ms:.2f}ms exceeds 100ms target"
                    )
                
                # Track message ID for deduplication
                self._sent_message_ids.append(notification.message_id)
                self._cleanup_sent_ids()
                
                self._logger.debug(
                    f"Score notification sent: {notification.message_id}"
                )
                return True
                
            except asyncio.TimeoutError:
                self._logger.warning(
                    f"Score notification send timeout: {notification.message_id}"
                )
                return await self._buffer_score_notification(notification)
            except Exception as e:
                self._logger.error(
                    f"Failed to send score notification: {e}"
                )
                self._connected = False
                if await self._attempt_reconnect():
                    return await self._send_message_internal(notification)
                return await self._buffer_score_notification(notification)
    
    async def _buffer_score_notification(
        self,
        notification: ConfidenceScoreUpdate | AlertNotification | ConfidenceScoreRefresh,
    ) -> bool:
        """
        Buffer score notification for later delivery.
        
        Args:
            notification: The notification to buffer
            
        Returns:
            True if buffered successfully
        """
        # For score notifications, we use a separate buffer
        # to maintain order with other notifications
        if not hasattr(self, '_score_buffer'):
            self._score_buffer: Deque = deque(maxlen=self.config.buffer_size)
        
        if len(self._score_buffer) >= self.config.buffer_size:
            self._logger.warning(
                f"Score buffer overflow, dropping oldest notification"
            )
            try:
                self._score_buffer.popleft()
            except IndexError:
                pass
        
        self._score_buffer.append(notification)
        self._logger.debug(
            f"Score notification buffered (buffer size: {len(self._score_buffer)})"
        )
        return True
    
    async def _flush_score_buffer(self) -> None:
        """
        Flush buffered score notifications on reconnection.
        """
        if not hasattr(self, '_score_buffer') or not self._score_buffer:
            return
        
        self._logger.info(
            f"Flushing {len(self._score_buffer)} buffered score notifications"
        )
        
        messages_to_send = list(self._score_buffer)
        self._score_buffer.clear()
        
        for notification in messages_to_send:
            if notification.message_id not in self._sent_message_ids:
                await self._send_message_internal(notification)
        
        self._logger.info("Score buffer flush completed")

    # === Health Status Notification Methods (Story 5.3) ===

    async def send_health_status_update(
        self,
        selector_id: str,
        old_status: str,
        new_status: str,
        confidence_score: Optional[float] = None,
    ) -> bool:
        """
        Send health status change notification (AC1).
        
        When a selector's health status changes in the adaptive module,
        this sends a notification with the status change details.
        
        Args:
            selector_id: ID/name of the selector
            old_status: Previous health status
            new_status: New health status
            confidence_score: Optional current confidence score
            
        Returns:
            True if sent or buffered successfully
        """
        notification = HealthStatusUpdate(
            selector_id=selector_id,
            old_status=HealthStatus(old_status),
            new_status=HealthStatus(new_status),
            confidence_score=confidence_score,
        )
        
        return await self._send_health_notification(notification)

    async def send_health_snapshot(
        self,
        health_statuses: list[dict],
    ) -> bool:
        """
        Send periodic health snapshot broadcast (AC2).
        
        Periodically broadcasts current health status for all selectors.
        
        Args:
            health_statuses: List of selector health statuses
                           Each dict should have: selector_id, status, confidence_score
            
        Returns:
            True if sent or buffered successfully
        """
        snapshot_list = []
        for status_dict in health_statuses:
            snapshot_list.append(
                SelectorHealthStatus(
                    selector_id=status_dict.get("selector_id", ""),
                    status=HealthStatus(status_dict.get("status", "unknown")),
                    confidence_score=status_dict.get("confidence_score"),
                    last_updated=status_dict.get("last_updated", datetime.now(timezone.utc)),
                )
            )
        
        notification = HealthSnapshot(
            snapshot=snapshot_list,
        )
        
        return await self._send_health_notification(notification)

    async def _send_health_notification(
        self,
        notification: HealthStatusUpdate | HealthSnapshot,
    ) -> bool:
        """
        Internal method to send health status notifications.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if sent or buffered successfully
        """
        # Check for duplicate
        if notification.message_id in self._sent_message_ids:
            self._logger.debug(
                f"Duplicate health notification skipped: {notification.message_id}"
            )
            return True
        
        # Try to send if connected
        if self._connected and self._websocket:
            return await self._send_health_message(notification)
        
        # Not connected - buffer the message
        return await self._buffer_health_notification(notification)

    async def _send_health_message(
        self,
        notification: HealthStatusUpdate | HealthSnapshot,
    ) -> bool:
        """
        Send a health notification via WebSocket.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if sent successfully
        """
        async with self._send_lock:
            try:
                message_json = notification.to_json()
                
                # Track latency
                send_start = datetime.now(timezone.utc)
                
                await asyncio.wait_for(
                    self._websocket.send(message_json),
                    timeout=self.config.message_timeout
                )
                
                # Calculate and record latency
                latency_ms = (datetime.now(timezone.utc) - send_start).total_seconds() * 1000
                self._notification_latencies.append(latency_ms)
                if latency_ms > 100:
                    self._logger.warning(
                        f"Health notification latency {latency_ms:.2f}ms exceeds 100ms target"
                    )
                
                # Track message ID for deduplication
                self._sent_message_ids.append(notification.message_id)
                self._cleanup_sent_ids()
                
                self._logger.debug(
                    f"Health notification sent: {notification.message_id}"
                )
                return True
                
            except asyncio.TimeoutError:
                self._logger.warning(
                    f"Health notification send timeout: {notification.message_id}"
                )
                return await self._buffer_health_notification(notification)
            except Exception as e:
                self._logger.error(
                    f"Failed to send health notification: {e}"
                )
                self._connected = False
                if await self._attempt_reconnect():
                    return await self._send_health_message(notification)
                return await self._buffer_health_notification(notification)

    async def _buffer_health_notification(
        self,
        notification: HealthStatusUpdate | HealthSnapshot,
    ) -> bool:
        """
        Buffer health notification for later delivery.
        
        Args:
            notification: The notification to buffer
            
        Returns:
            True if buffered successfully
        """
        if not hasattr(self, '_health_buffer'):
            self._health_buffer: Deque = deque(maxlen=self.config.buffer_size)
        
        if len(self._health_buffer) >= self.config.buffer_size:
            self._logger.warning(
                f"Health buffer overflow, dropping oldest notification"
            )
            try:
                self._health_buffer.popleft()
            except IndexError:
                pass
        
        self._health_buffer.append(notification)
        self._logger.debug(
            f"Health notification buffered (buffer size: {len(self._health_buffer)})"
        )
        return True

    async def _flush_health_buffer(self) -> None:
        """
        Flush buffered health notifications on reconnection.
        """
        if not hasattr(self, '_health_buffer') or not self._health_buffer:
            return
        
        self._logger.info(
            f"Flushing {len(self._health_buffer)} buffered health notifications"
        )
        
        messages_to_send = list(self._health_buffer)
        self._health_buffer.clear()
        
        for notification in messages_to_send:
            if notification.message_id not in self._sent_message_ids:
                await self._send_health_message(notification)
        
        self._logger.info("Health buffer flush completed")
    
    @asynccontextmanager
    async def session(self):
        """
        Async context manager for WebSocket session.
        
        Usage:
            async with client.session():
                await client.send_failure(...)
        """
        self._running = True
        try:
            await self.connect()
            yield self
        finally:
            self._running = False
            await self.disconnect()
    
    async def start_background(self) -> None:
        """
        Start background connection management.
        
        This method runs a background task that maintains the connection
        and handles reconnection automatically.
        """
        self._running = True
        
        async def _keep_alive():
            while self._running:
                try:
                    if not self._connected:
                        await self.connect()
                    elif self._websocket:
                        # Send ping to keep connection alive
                        try:
                            await self._websocket.ping()
                        except Exception as e:
                            self._logger.warning(f"Ping failed: {e}")
                            self._connected = False
                            await self._attempt_reconnect()
                except Exception as e:
                    self._logger.error(f"Background task error: {e}")
                
                await asyncio.sleep(self.config.ping_interval)
        
        # Store task reference for management/cancellation
        self._background_task = asyncio.create_task(_keep_alive())
    
    async def stop_background(self) -> None:
        """Stop background connection management."""
        self._running = False
        if self._background_task:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
        await self.disconnect()

    # === Blast Radius Notification Methods (Story 6.3) ===

    async def send_blast_radius_update(
        self,
        failed_selector: str,
        severity: str,
        affected_fields: list[str],
        affected_records: int,
        confidence_score: float,
        recommended_actions: Optional[list[str]] = None,
        cascading_selectors: Optional[list[str]] = None,
    ) -> bool:
        """
        Send blast radius update notification (AC5).
        
        When a selector fails and blast radius is calculated,
        this sends a notification with the blast radius details.
        
        Args:
            failed_selector: The selector ID that failed
            severity: Severity level (critical/major/minor)
            affected_fields: List of affected field names
            affected_records: Count of affected records
            confidence_score: Current confidence score
            recommended_actions: Optional list of recommended actions
            cascading_selectors: Optional list of related selectors potentially impacted (AC3)
            
        Returns:
            True if sent or buffered successfully
        """
        notification = BlastRadiusUpdate(
            failed_selector=failed_selector,
            severity=BlastRadiusSeverity(severity),
            affected_fields=affected_fields,
            affected_records=affected_records,
            confidence_score=confidence_score,
            recommended_actions=recommended_actions or [],
            cascading_selectors=cascading_selectors or [],
        )
        
        return await self._send_blast_radius_notification(notification)

    async def _send_blast_radius_notification(
        self,
        notification: BlastRadiusUpdate,
    ) -> bool:
        """
        Internal method to send blast radius notifications.
        
        Args:
            notification: The notification to send
            
        Returns:
            True if sent or buffered successfully
        """
        # Check for duplicate
        if notification.message_id in self._sent_message_ids:
            self._logger.debug(
                f"Duplicate blast radius notification skipped: {notification.message_id}"
            )
            return True
        
        # Try to send if connected
        if self._websocket and self._connected:
            try:
                message_json = notification.to_json()
                send_start = datetime.now(timezone.utc)
                
                await asyncio.wait_for(
                    self._websocket.send(message_json),
                    timeout=self.config.message_timeout
                )
                
                # Calculate and record latency
                latency_ms = (datetime.now(timezone.utc) - send_start).total_seconds() * 1000
                self._notification_latencies.append(latency_ms)
                
                # Track message ID for deduplication
                self._sent_message_ids.append(notification.message_id)
                self._cleanup_sent_ids()
                
                self._logger.debug(
                    f"Blast radius notification sent: {notification.message_id}"
                )
                return True
                
            except asyncio.TimeoutError:
                self._logger.warning(
                    f"Blast radius notification send timeout: {notification.message_id}"
                )
                return await self._buffer_blast_radius_notification(notification)
            except Exception as e:
                self._logger.error(
                    f"Failed to send blast radius notification: {e}"
                )
                self._connected = False
                if await self._attempt_reconnect():
                    return await self._send_blast_radius_notification(notification)
                return await self._buffer_blast_radius_notification(notification)
        
        # Not connected, buffer the notification
        return await self._buffer_blast_radius_notification(notification)

    async def _buffer_blast_radius_notification(
        self,
        notification: BlastRadiusUpdate,
    ) -> bool:
        """
        Buffer blast radius notification for later delivery.
        
        Args:
            notification: The notification to buffer
            
        Returns:
            True if buffered successfully
        """
        if not hasattr(self, '_blast_radius_buffer'):
            self._blast_radius_buffer: Deque = deque(maxlen=self.config.buffer_size)
        
        if len(self._blast_radius_buffer) >= self.config.buffer_size:
            self._logger.warning(
                f"Blast radius buffer overflow, dropping oldest notification"
            )
            try:
                self._blast_radius_buffer.popleft()
            except IndexError:
                pass
        
        self._blast_radius_buffer.append(notification)
        self._logger.debug(
            f"Blast radius notification buffered (buffer size: {len(self._blast_radius_buffer)})"
        )
        return True

    async def _flush_blast_radius_buffer(self) -> None:
        """
        Flush buffered blast radius notifications on reconnection.
        """
        if not hasattr(self, '_blast_radius_buffer') or not self._blast_radius_buffer:
            return
        
        self._logger.info(
            f"Flushing blast radius buffer: {len(self._blast_radius_buffer)} notifications"
        )
        
        # Create a copy of the buffer and clear it
        buffer_copy = list(self._blast_radius_buffer)
        self._blast_radius_buffer.clear()
        
        # Send each notification
        for notification in buffer_copy:
            try:
                await self._send_blast_radius_notification(notification)
            except Exception as e:
                self._logger.error(
                    f"Failed to flush blast radius notification: {e}"
                )
        
        self._logger.info("Blast radius buffer flush completed")
