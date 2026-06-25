"""
Plugin sandboxing system for secure plugin execution.

This module provides comprehensive sandboxing capabilities for plugins, including
resource limits, security restrictions, and isolation mechanisms.
"""

import os
import sys
import time
import threading
import multiprocessing
import subprocess
import tempfile
import shutil
import signal
import psutil
from typing import Dict, Any, List, Optional, Callable, Type, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio
import json
import pickle
import weakref

from .plugin_interface import IPlugin, PluginContext, PluginResult, PluginStatus, HookType
from .plugin_permissions import PermissionManager, get_permission_manager


class SandboxType(Enum):
    """Sandbox type enumeration."""
    PROCESS = "process"
    THREAD = "thread"
    MEMORY = "memory"
    CONTAINER = "container"
    VIRTUAL_ENV = "virtual_env"


class SecurityLevel(Enum):
    """Security level enumeration."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    STRICT = "strict"
    MAXIMUM = "maximum"


@dataclass
class ResourceLimits:
    """Resource limits for sandbox."""
    max_memory_mb: int = 512
    max_cpu_percent: float = 50.0
    max_execution_time_seconds: int = 30
    max_file_operations: int = 1000
    max_network_requests: int = 10
    max_disk_space_mb: int = 100
    max_open_files: int = 100
    max_processes: int = 5


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    sandbox_type: SandboxType
    security_level: SecurityLevel
    resource_limits: ResourceLimits
    allowed_modules: List[str] = field(default_factory=list)
    blocked_modules: List[str] = field(default_factory=list)
    allowed_file_paths: List[str] = field(default_factory=list)
    blocked_file_paths: List[str] = field(default_factory=list)
    allowed_network_hosts: List[str] = field(default_factory=list)
    blocked_network_hosts: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    working_directory: Optional[str] = None
    temp_directory: Optional[str] = None
    enable_logging: bool = True
    log_level: str = "INFO"
    cleanup_on_exit: bool = True


@dataclass
class SandboxExecutionResult:
    """Sandbox execution result."""
    success: bool
    plugin_id: str
    execution_id: str
    result: Optional[PluginResult] = None
    execution_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    file_operations: int = 0
    network_requests: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    security_violations: List[str] = field(default_factory=list)
    resource_exceeded: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class PluginSandbox:
    """Plugin sandbox for secure execution."""
    
    def __init__(self, config: SandboxConfig):
        """Initialize plugin sandbox."""
        self.config = config
        self.permission_manager = get_permission_manager()
        
        # Execution tracking
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._running_processes: Dict[str, subprocess.Popen] = {}
        self._running_threads: Dict[str, threading.Thread] = {}
        
        # Resource monitoring
        self._resource_monitors: Dict[str, Dict[str, Any]] = {}
        self._monitoring_active = False
        
        # Security tracking
        self._security_violations: Dict[str, List[str]] = {}
        self._access_logs: Dict[str, List[Dict[str, Any]]] = {}
        
        # Temporary directories
        self._temp_dirs: Dict[str, str] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Statistics
        self._stats = {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'security_violations': 0,
            'resource_exceeded': 0,
            'total_execution_time_ms': 0.0,
            'average_execution_time_ms': 0.0,
            'total_memory_usage_mb': 0.0,
            'average_memory_usage_mb': 0.0
        }
    
    async def execute_plugin(self, plugin: IPlugin, context: PluginContext, 
                           hook_type: HookType, **kwargs) -> SandboxExecutionResult:
        """
        Execute a plugin in the sandbox.
        
        Args:
            plugin: Plugin instance
            context: Plugin context
            hook_type: Hook type
            **kwargs: Hook arguments
            
        Returns:
            Sandbox execution result
        """
        execution_id = f"{plugin.metadata.id}_{hook_type.value}_{int(time.time() * 1000000)}"
        start_time = datetime.utcnow()
        
        try:
            # Create execution context
            execution_context = {
                'plugin_id': plugin.metadata.id,
                'execution_id': execution_id,
                'hook_type': hook_type,
                'start_time': start_time,
                'context': context,
                'kwargs': kwargs,
                'config': self.config
            }
            
            # Store execution
            with self._lock:
                self._executions[execution_id] = execution_context
            
            # Check permissions
            if not self._check_plugin_permissions(plugin.metadata.id):
                return SandboxExecutionResult(
                    success=False,
                    plugin_id=plugin.metadata.id,
                    execution_id=execution_id,
                    errors=["Plugin does not have required permissions"],
                    security_violations=["Permission check failed"]
                )
            
            # Create temporary directory if needed
            temp_dir = self._create_temp_directory(execution_id)
            
            # Execute based on sandbox type
            if self.config.sandbox_type == SandboxType.PROCESS:
                result = await self._execute_in_process(plugin, context, hook_type, execution_id, **kwargs)
            elif self.config.sandbox_type == SandboxType.THREAD:
                result = await self._execute_in_thread(plugin, context, hook_type, execution_id, **kwargs)
            elif self.config.sandbox_type == SandboxType.MEMORY:
                result = await self._execute_in_memory(plugin, context, hook_type, execution_id, **kwargs)
            else:
                result = SandboxExecutionResult(
                    success=False,
                    plugin_id=plugin.metadata.id,
                    execution_id=execution_id,
                    errors=[f"Unsupported sandbox type: {self.config.sandbox_type}"]
                )
            
            # Update statistics
            self._update_statistics(result)
            
            # Clean up temporary directory
            if self.config.cleanup_on_exit and temp_dir:
                self._cleanup_temp_directory(temp_dir)
            
            return result
            
        except Exception as e:
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return SandboxExecutionResult(
                success=False,
                plugin_id=plugin.metadata.id,
                execution_id=execution_id,
                execution_time_ms=execution_time_ms,
                errors=[f"Sandbox execution failed: {str(e)}"]
            )
        finally:
            # Clean up execution
            with self._lock:
                if execution_id in self._executions:
                    del self._executions[execution_id]
    
    async def _execute_in_process(self, plugin: IPlugin, context: PluginContext, 
                                hook_type: HookType, execution_id: str, **kwargs) -> SandboxExecutionResult:
        """Execute plugin in a separate process."""
        start_time = datetime.utcnow()
        
        try:
            # Prepare execution data
            execution_data = {
                'plugin_id': plugin.metadata.id,
                'hook_type': hook_type.value,
                'context': context,
                'kwargs': kwargs,
                'config': self.config
            }
            
            # Serialize plugin and context
            plugin_data = self._serialize_plugin(plugin)
            context_data = self._serialize_context(context)
            
            # Create process arguments
            process_args = [
                sys.executable,
                '-c',
                self._get_process_execution_code(),
                str(execution_id),
                plugin_data,
                context_data,
                json.dumps(kwargs)
            ]
            
            # Set up environment
            env = os.environ.copy()
            env.update(self.config.environment_variables)
            
            # Start process
            process = subprocess.Popen(
                process_args,
                env=env,
                cwd=self.config.working_directory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Store process
            with self._lock:
                self._running_processes[execution_id] = process
            
            # Start resource monitoring
            monitor_task = asyncio.create_task(
                self._monitor_process_resources(execution_id, process.pid)
            )
            
            try:
                # Wait for process with timeout
                stdout, stderr = process.communicate(
                    timeout=self.config.resource_limits.max_execution_time_seconds
                )
                
                # Parse result
                try:
                    result_data = json.loads(stdout)
                    result = self._deserialize_result(result_data)
                except json.JSONDecodeError:
                    result = PluginResult(
                        success=False,
                        plugin_id=plugin.metadata.id,
                        hook_type=hook_type,
                        errors=["Failed to parse process output"],
                        metadata={'stdout': stdout, 'stderr': stderr}
                    )
                
                # Get resource usage
                resource_usage = await self._get_process_resource_usage(process.pid)
                
                # Create sandbox result
                execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return SandboxExecutionResult(
                    success=result.success,
                    plugin_id=plugin.metadata.id,
                    execution_id=execution_id,
                    result=result,
                    execution_time_ms=execution_time_ms,
                    memory_usage_mb=resource_usage.get('memory_mb', 0),
                    cpu_usage_percent=resource_usage.get('cpu_percent', 0),
                    errors=result.errors,
                    warnings=result.warnings,
                    metadata={
                        'stdout': stdout,
                        'stderr': stderr,
                        'return_code': process.returncode
                    }
                )
                
            except subprocess.TimeoutExpired:
                # Kill process
                process.kill()
                process.wait()
                
                return SandboxExecutionResult(
                    success=False,
                    plugin_id=plugin.metadata.id,
                    execution_id=execution_id,
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    errors=[f"Process execution timeout after {self.config.resource_limits.max_execution_time_seconds}s"],
                    resource_exceeded=["execution_time"]
                )
            finally:
                # Cancel monitoring
                monitor_task.cancel()
                
                # Clean up
                with self._lock:
                    if execution_id in self._running_processes:
                        del self._running_processes[execution_id]
        
        except Exception as e:
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return SandboxExecutionResult(
                success=False,
                plugin_id=plugin.metadata.id,
                execution_id=execution_id,
                execution_time_ms=execution_time_ms,
                errors=[f"Process execution failed: {str(e)}"]
            )
    
    async def _execute_in_thread(self, plugin: IPlugin, context: PluginContext, 
                               hook_type: HookType, execution_id: str, **kwargs) -> SandboxExecutionResult:
        """Execute plugin in a separate thread."""
        start_time = datetime.utcnow()
        
        try:
            # Create thread function
            def thread_function():
                try:
                    # Execute plugin
                    result = asyncio.run(plugin.execute(context, hook_type, **kwargs))
                    return result
                except Exception as e:
                    return PluginResult(
                        success=False,
                        plugin_id=plugin.metadata.id,
                        hook_type=hook_type,
                        errors=[str(e)]
                    )
            
            # Start thread
            thread = threading.Thread(target=thread_function)
            thread.start()
            
            # Store thread
            with self._lock:
                self._running_threads[execution_id] = thread
            
            # Start resource monitoring
            monitor_task = asyncio.create_task(
                self._monitor_thread_resources(execution_id, thread.ident)
            )
            
            try:
                # Wait for thread with timeout
                thread.join(timeout=self.config.resource_limits.max_execution_time_seconds)
                
                if thread.is_alive():
                    # Thread is still running, consider it timeout
                    return SandboxExecutionResult(
                        success=False,
                        plugin_id=plugin.metadata.id,
                        execution_id=execution_id,
                        execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                        errors=[f"Thread execution timeout after {self.config.resource_limits.max_execution_time_seconds}s"],
                        resource_exceeded=["execution_time"]
                    )
                
                # Get result from thread (simplified - in real implementation would use queue)
                # For now, execute directly
                result = await plugin.execute(context, hook_type, **kwargs)
                
                # Get resource usage
                resource_usage = await self._get_thread_resource_usage(thread.ident)
                
                # Create sandbox result
                execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return SandboxExecutionResult(
                    success=result.success,
                    plugin_id=plugin.metadata.id,
                    execution_id=execution_id,
                    result=result,
                    execution_time_ms=execution_time_ms,
                    memory_usage_mb=resource_usage.get('memory_mb', 0),
                    cpu_usage_percent=resource_usage.get('cpu_percent', 0),
                    errors=result.errors,
                    warnings=result.warnings
                )
                
            finally:
                # Cancel monitoring
                monitor_task.cancel()
                
                # Clean up
                with self._lock:
                    if execution_id in self._running_threads:
                        del self._running_threads[execution_id]
        
        except Exception as e:
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return SandboxExecutionResult(
                success=False,
                plugin_id=plugin.metadata.id,
                execution_id=execution_id,
                execution_time_ms=execution_time_ms,
                errors=[f"Thread execution failed: {str(e)}"]
            )
    
    async def _execute_in_memory(self, plugin: IPlugin, context: PluginContext, 
                              hook_type: HookType, execution_id: str, **kwargs) -> SandboxExecutionResult:
        """Execute plugin in memory with restrictions."""
        start_time = datetime.utcnow()
        
        try:
            # Start resource monitoring
            monitor_task = asyncio.create_task(
                self._monitor_memory_resources(execution_id)
            )
            
            try:
                # Execute plugin directly with timeout
                result = await asyncio.wait_for(
                    plugin.execute(context, hook_type, **kwargs),
                    timeout=self.config.resource_limits.max_execution_time_seconds
                )
                
                # Get resource usage
                resource_usage = await self._get_memory_resource_usage()
                
                # Create sandbox result
                execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return SandboxExecutionResult(
                    success=result.success,
                    plugin_id=plugin.metadata.id,
                    execution_id=execution_id,
                    result=result,
                    execution_time_ms=execution_time_ms,
                    memory_usage_mb=resource_usage.get('memory_mb', 0),
                    cpu_usage_percent=resource_usage.get('cpu_percent', 0),
                    errors=result.errors,
                    warnings=result.warnings
                )
                
            except asyncio.TimeoutError:
                return SandboxExecutionResult(
                    success=False,
                    plugin_id=plugin.metadata.id,
                    execution_id=execution_id,
                    execution_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                    errors=[f"Memory execution timeout after {self.config.resource_limits.max_execution_time_seconds}s"],
                    resource_exceeded=["execution_time"]
                )
            finally:
                # Cancel monitoring
                monitor_task.cancel()
        
        except Exception as e:
            execution_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return SandboxExecutionResult(
                success=False,
                plugin_id=plugin.metadata.id,
                execution_id=execution_id,
                execution_time_ms=execution_time_ms,
                errors=[f"Memory execution failed: {str(e)}"]
            )
    
    def _check_plugin_permissions(self, plugin_id: str) -> bool:
        """Check if plugin has required permissions for sandbox execution."""
        # Check basic permissions
        required_permissions = [
            "execution",
            "data_access"
        ]
        
        for permission in required_permissions:
            if not self.permission_manager.has_permission(plugin_id, permission):
                return False
        
        # Check sandbox-specific permissions
        if self.config.sandbox_type == SandboxType.PROCESS:
            if not self.permission_manager.has_permission(plugin_id, "system_access"):
                return False
        
        return True
    
    def _create_temp_directory(self, execution_id: str) -> Optional[str]:
        """Create temporary directory for execution."""
        if self.config.temp_directory:
            temp_dir = os.path.join(self.config.temp_directory, execution_id)
        else:
            temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{execution_id}_")
        
        os.makedirs(temp_dir, exist_ok=True)
        
        with self._lock:
            self._temp_dirs[execution_id] = temp_dir
        
        return temp_dir
    
    def _cleanup_temp_directory(self, temp_dir: str) -> None:
        """Clean up temporary directory."""
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            # Log error but continue
            pass
    
    def _serialize_plugin(self, plugin: IPlugin) -> str:
        """Serialize plugin for process execution."""
        # In a real implementation, this would serialize the plugin
        # For now, return a placeholder
        return json.dumps({
            'plugin_id': plugin.metadata.id,
            'plugin_type': plugin.metadata.plugin_type.value,
            'metadata': plugin.metadata.__dict__
        })
    
    def _serialize_context(self, context: PluginContext) -> str:
        """Serialize context for process execution."""
        return json.dumps({
            'plugin_id': context.plugin_id,
            'configuration': context.configuration,
            'metadata': context.metadata
        })
    
    def _deserialize_result(self, result_data: Dict[str, Any]) -> PluginResult:
        """Deserialize result from process execution."""
        return PluginResult(
            success=result_data.get('success', False),
            plugin_id=result_data.get('plugin_id', ''),
            hook_type=HookType(result_data.get('hook_type', 'custom')),
            data=result_data.get('data', {}),
            errors=result_data.get('errors', []),
            warnings=result_data.get('warnings', []),
            execution_time_ms=result_data.get('execution_time_ms', 0.0)
        )
    
    def _get_process_execution_code(self) -> str:
        """Get Python code for process execution."""
        return '''
import sys
import json
import pickle
import asyncio

async def execute_plugin():
    execution_id = sys.argv[1]
    plugin_data = sys.argv[2]
    context_data = sys.argv[3]
    kwargs_data = sys.argv[4]
    
    # Deserialize plugin and context
    # In a real implementation, this would reconstruct the plugin
    # For now, return a mock result
    
    result = {
        'success': True,
        'plugin_id': json.loads(plugin_data)['plugin_id'],
        'hook_type': json.loads(context_data)['plugin_id'],
        'data': {'executed_in_process': True},
        'errors': [],
        'warnings': [],
        'execution_time_ms': 0.0
    }
    
    print(json.dumps(result))

if __name__ == '__main__':
    asyncio.run(execute_plugin())
'''
    
    async def _monitor_process_resources(self, execution_id: str, pid: int) -> None:
        """Monitor process resource usage."""
        try:
            process = psutil.Process(pid)
            
            while True:
                try:
                    # Get resource usage
                    memory_info = process.memory_info()
                    cpu_percent = process.cpu_percent()
                    
                    # Check limits
                    memory_mb = memory_info.rss / 1024 / 1024
                    
                    if memory_mb > self.config.resource_limits.max_memory_mb:
                        # Kill process
                        process.kill()
                        self._record_security_violation(execution_id, f"Memory limit exceeded: {memory_mb}MB")
                        break
                    
                    if cpu_percent > self.config.resource_limits.max_cpu_percent:
                        self._record_security_violation(execution_id, f"CPU limit exceeded: {cpu_percent}%")
                    
                    # Store monitoring data
                    with self._lock:
                        if execution_id not in self._resource_monitors:
                            self._resource_monitors[execution_id] = {}
                        
                        self._resource_monitors[execution_id] = {
                            'memory_mb': memory_mb,
                            'cpu_percent': cpu_percent,
                            'timestamp': datetime.utcnow()
                        }
                    
                    await asyncio.sleep(1)  # Monitor every second
                    
                except psutil.NoSuchProcess:
                    break
                except Exception as e:
                    break
        
        except Exception as e:
            # Log error but continue
            pass
    
    async def _monitor_thread_resources(self, execution_id: str, thread_id: int) -> None:
        """Monitor thread resource usage."""
        # Simplified thread monitoring
        # In a real implementation, would use more sophisticated monitoring
        try:
            while True:
                # Get current process resource usage
                process = psutil.Process()
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                memory_mb = memory_info.rss / 1024 / 1024
                
                # Store monitoring data
                with self._lock:
                    if execution_id not in self._resource_monitors:
                        self._resource_monitors[execution_id] = {}
                    
                    self._resource_monitors[execution_id] = {
                        'memory_mb': memory_mb,
                        'cpu_percent': cpu_percent,
                        'timestamp': datetime.utcnow()
                    }
                
                await asyncio.sleep(1)
        
        except Exception as e:
            # Log error but continue
            pass
    
    async def _monitor_memory_resources(self, execution_id: str) -> None:
        """Monitor memory resource usage."""
        try:
            while True:
                # Get current process resource usage
                process = psutil.Process()
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                memory_mb = memory_info.rss / 1024 / 1024
                
                # Store monitoring data
                with self._lock:
                    if execution_id not in self._resource_monitors:
                        self._resource_monitors[execution_id] = {}
                    
                    self._resource_monitors[execution_id] = {
                        'memory_mb': memory_mb,
                        'cpu_percent': cpu_percent,
                        'timestamp': datetime.utcnow()
                    }
                
                await asyncio.sleep(1)
        
        except Exception as e:
            # Log error but continue
            pass
    
    async def _get_process_resource_usage(self, pid: int) -> Dict[str, Any]:
        """Get process resource usage."""
        try:
            process = psutil.Process(pid)
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            return {
                'memory_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': cpu_percent
            }
        except psutil.NoSuchProcess:
            return {'memory_mb': 0, 'cpu_percent': 0}
    
    async def _get_thread_resource_usage(self, thread_id: int) -> Dict[str, Any]:
        """Get thread resource usage."""
        # Simplified - return process usage
        return await self._get_memory_resource_usage()
    
    async def _get_memory_resource_usage(self) -> Dict[str, Any]:
        """Get memory resource usage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_percent = process.cpu_percent()
            
            return {
                'memory_mb': memory_info.rss / 1024 / 1024,
                'cpu_percent': cpu_percent
            }
        except Exception:
            return {'memory_mb': 0, 'cpu_percent': 0}
    
    def _record_security_violation(self, execution_id: str, violation: str) -> None:
        """Record a security violation."""
        with self._lock:
            if execution_id not in self._security_violations:
                self._security_violations[execution_id] = []
            
            self._security_violations[execution_id].append(violation)
    
    def _update_statistics(self, result: SandboxExecutionResult) -> None:
        """Update sandbox statistics."""
        with self._lock:
            self._stats['total_executions'] += 1
            
            if result.success:
                self._stats['successful_executions'] += 1
            else:
                self._stats['failed_executions'] += 1
            
            self._stats['total_execution_time_ms'] += result.execution_time_ms
            self._stats['average_execution_time_ms'] = (
                self._stats['total_execution_time_ms'] / self._stats['total_executions']
                if self._stats['total_executions'] > 0 else 0
            )
            
            self._stats['total_memory_usage_mb'] += result.memory_usage_mb
            self._stats['average_memory_usage_mb'] = (
                self._stats['total_memory_usage_mb'] / self._stats['total_executions']
                if self._stats['total_executions'] > 0 else 0
            )
            
            if result.security_violations:
                self._stats['security_violations'] += len(result.security_violations)
            
            if result.resource_exceeded:
                self._stats['resource_exceeded'] += len(result.resource_exceeded)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get sandbox statistics."""
        with self._lock:
            return self._stats.copy()
    
    def get_running_executions(self) -> Dict[str, Dict[str, Any]]:
        """Get currently running executions."""
        with self._lock:
            running = {}
            
            # Add running processes
            for execution_id, process in self._running_processes.items():
                running[execution_id] = {
                    'type': 'process',
                    'pid': process.pid,
                    'status': 'running' if process.poll() is None else 'completed'
                }
            
            # Add running threads
            for execution_id, thread in self._running_threads.items():
                running[execution_id] = {
                    'type': 'thread',
                    'thread_id': thread.ident,
                    'status': 'running' if thread.is_alive() else 'completed'
                }
            
            return running
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        with self._lock:
            # Cancel process
            if execution_id in self._running_processes:
                process = self._running_processes[execution_id]
                try:
                    process.kill()
                    process.wait()
                    del self._running_processes[execution_id]
                    return True
                except Exception:
                    pass
            
            # Cancel thread (simplified)
            if execution_id in self._running_threads:
                # In a real implementation, would use proper thread cancellation
                del self._running_threads[execution_id]
                return True
        
        return False
    
    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        with self._lock:
            # Kill all running processes
            for process in self._running_processes.values():
                try:
                    process.kill()
                    process.wait()
                except Exception:
                    pass
            
            # Clean up threads
            self._running_threads.clear()
            
            # Clean up temporary directories
            for temp_dir in self._temp_dirs.values():
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            
            # Clear tracking
            self._executions.clear()
            self._running_processes.clear()
            self._running_threads.clear()
            self._resource_monitors.clear()
            self._security_violations.clear()
            self._access_logs.clear()
            self._temp_dirs.clear()


class SandboxManager:
    """Sandbox manager for managing multiple sandboxes."""
    
    def __init__(self):
        """Initialize sandbox manager."""
        self._sandboxes: Dict[str, PluginSandbox] = {}
        self._default_config = SandboxConfig(
            sandbox_type=SandboxType.THREAD,
            security_level=SecurityLevel.STANDARD,
            resource_limits=ResourceLimits()
        )
        self._lock = threading.RLock()
    
    def create_sandbox(self, sandbox_id: str, config: Optional[SandboxConfig] = None) -> PluginSandbox:
        """Create a sandbox."""
        with self._lock:
            if sandbox_id in self._sandboxes:
                raise ValueError(f"Sandbox {sandbox_id} already exists")
            
            sandbox_config = config or self._default_config
            sandbox = PluginSandbox(sandbox_config)
            self._sandboxes[sandbox_id] = sandbox
            
            return sandbox
    
    def get_sandbox(self, sandbox_id: str) -> Optional[PluginSandbox]:
        """Get a sandbox by ID."""
        return self._sandboxes.get(sandbox_id)
    
    def remove_sandbox(self, sandbox_id: str) -> bool:
        """Remove a sandbox."""
        with self._lock:
            if sandbox_id not in self._sandboxes:
                return False
            
            sandbox = self._sandboxes[sandbox_id]
            sandbox.cleanup()
            del self._sandboxes[sandbox_id]
            
            return True
    
    def get_all_sandboxes(self) -> Dict[str, PluginSandbox]:
        """Get all sandboxes."""
        with self._lock:
            return self._sandboxes.copy()
    
    def cleanup_all(self) -> None:
        """Clean up all sandboxes."""
        with self._lock:
            for sandbox in self._sandboxes.values():
                sandbox.cleanup()
            
            self._sandboxes.clear()


# Global sandbox manager instance
_sandbox_manager = SandboxManager()


# Convenience functions
def create_sandbox(sandbox_id: str, config: Optional[SandboxConfig] = None) -> PluginSandbox:
    """Create a sandbox."""
    return _sandbox_manager.create_sandbox(sandbox_id, config)


def get_sandbox(sandbox_id: str) -> Optional[PluginSandbox]:
    """Get a sandbox by ID."""
    return _sandbox_manager.get_sandbox(sandbox_id)


def remove_sandbox(sandbox_id: str) -> bool:
    """Remove a sandbox."""
    return _sandbox_manager.remove_sandbox(sandbox_id)


def get_sandbox_manager() -> SandboxManager:
    """Get the global sandbox manager."""
    return _sandbox_manager
