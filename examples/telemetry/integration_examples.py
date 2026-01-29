"""
Integration examples for the telemetry system.

This module provides practical examples of how to integrate the telemetry system
with selector operations and other components.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.telemetry.lifecycle import telemetry_system, get_lifecycle_manager
from src.telemetry.integration.selector_integration import SelectorTelemetryIntegration
from src.telemetry.configuration.telemetry_config import TelemetryConfiguration

logger = logging.getLogger(__name__)


# Example 1: Basic telemetry integration with selector engine
async def example_basic_integration():
    """Basic example of integrating telemetry with selector operations."""
    
    # Configuration for basic telemetry
    config = {
        "collection": {
            "enabled": True,
            "buffer_size": 1000,
            "batch_size": 100,
            "flush_interval": 1.0
        },
        "storage": {
            "type": "json",
            "directory": "telemetry_data",
            "retention_days": 30
        },
        "alerting": {
            "enabled": True,
            "thresholds": {
                "performance": {
                    "resolution_time_ms": 5000,
                    "memory_usage_mb": 100
                },
                "quality": {
                    "confidence_score": 0.7
                }
            }
        },
        "reporting": {
            "enabled": True,
            "types": ["performance", "usage"],
            "schedule": {
                "frequency": "daily",
                "time_of_day": "00:00"
            }
        },
        "performance": {
            "overhead_target_percent": 2.0,
            "memory_threshold_mb": 100
        }
    }
    
    # Use telemetry system context manager
    async with telemetry_system(config) as manager:
        # Create selector integration
        selector_integration = SelectorTelemetryIntegration()
        
        # Simulate selector operation
        correlation_id = "example_001"
        selector_id = "product_title"
        
        # Start telemetry collection
        await selector_integration.start_selector_operation(
            selector_id=selector_id,
            correlation_id=correlation_id,
            strategy="text_anchor"
        )
        
        # Simulate selector resolution
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Record successful resolution
        await selector_integration.record_selector_success(
            selector_id=selector_id,
            correlation_id=correlation_id,
            confidence_score=0.85,
            resolution_time_ms=100,
            elements_found=3
        )
        
        # Get system health
        health = await manager.get_health_status()
        print(f"System healthy: {health.healthy}")
        print(f"Memory usage: {health.memory_usage_mb:.1f}MB")
        
        # Get system metrics
        metrics = await manager.get_system_metrics()
        print(f"Operations: {metrics.total_operations}")
        print(f"Uptime: {metrics.uptime_seconds:.1f}s")


# Example 2: Advanced telemetry with InfluxDB
async def example_influxdb_integration():
    """Advanced example using InfluxDB for storage."""
    
    config = {
        "collection": {
            "enabled": True,
            "buffer_size": 5000,
            "batch_size": 500,
            "flush_interval": 0.5
        },
        "storage": {
            "type": "influxdb",
            "url": "http://localhost:8086",
            "token": "your-influxdb-token",
            "org": "your-org",
            "bucket": "telemetry",
            "batch_size": 500,
            "flush_interval": 0.5,
            "retention_days": 90
        },
        "alerting": {
            "enabled": True,
            "thresholds": {
                "performance": {
                    "resolution_time_ms": 2000,
                    "memory_usage_mb": 200,
                    "error_rate_percent": 5.0
                },
                "quality": {
                    "confidence_score": 0.8,
                    "decline_percent": 15.0
                },
                "health": {
                    "anomaly_threshold": 2.0,
                    "timeout_frequency_percent": 5.0
                }
            },
            "notifications": {
                "channels": ["log", "webhook"],
                "rate_limit": {
                    "max_per_hour": 20
                }
            }
        },
        "reporting": {
            "enabled": True,
            "types": ["performance", "usage", "health", "trends", "recommendations"],
            "schedule": {
                "frequency": "hourly",
                "time_of_day": "00:00"
            }
        },
        "performance": {
            "overhead_target_percent": 1.5,
            "memory_threshold_mb": 200,
            "cache": {
                "size": 2000,
                "ttl_seconds": 600
            }
        }
    }
    
    async with telemetry_system(config) as manager:
        selector_integration = SelectorTelemetryIntegration()
        
        # Simulate high-volume selector operations
        for i in range(100):
            correlation_id = f"batch_{i:03d}"
            selector_id = f"selector_{i % 10}"
            
            await selector_integration.start_selector_operation(
                selector_id=selector_id,
                correlation_id=correlation_id,
                strategy="attribute_match"
            )
            
            # Simulate varying performance
            await asyncio.sleep(0.01 + (i % 5) * 0.01)
            
            # Record results with varying confidence
            confidence = 0.9 - (i % 10) * 0.05
            await selector_integration.record_selector_success(
                selector_id=selector_id,
                correlation_id=correlation_id,
                confidence_score=confidence,
                resolution_time_ms=10 + (i % 3) * 5,
                elements_found=1 + (i % 4)
            )
        
        # Wait for data to be processed
        await asyncio.sleep(2)
        
        # Get detailed metrics
        health = await manager.get_health_status()
        print(f"Processed 100 operations")
        print(f"System healthy: {health.healthy}")
        print(f"Error rate: {(1 - health.error_rate) * 100:.1f}%")


# Example 3: Error handling and recovery
async def example_error_handling():
    """Example demonstrating error handling and recovery."""
    
    config = {
        "collection": {
            "enabled": True,
            "buffer_size": 100,
            "batch_size": 10
        },
        "storage": {
            "type": "json",
            "directory": "/invalid/path/that/does/not/exist",  # This will cause errors
            "retention_days": 30
        },
        "alerting": {
            "enabled": True,
            "thresholds": {
                "performance": {
                    "resolution_time_ms": 1000
                }
            }
        }
    }
    
    try:
        async with telemetry_system(config) as manager:
            selector_integration = SelectorTelemetryIntegration()
            
            # This will trigger storage errors and recovery attempts
            for i in range(5):
                correlation_id = f"error_test_{i}"
                selector_id = "test_selector"
                
                await selector_integration.start_selector_operation(
                    selector_id=selector_id,
                    correlation_id=correlation_id,
                    strategy="text_anchor"
                )
                
                await selector_integration.record_selector_success(
                    selector_id=selector_id,
                    correlation_id=correlation_id,
                    confidence_score=0.8,
                    resolution_time_ms=50,
                    elements_found=1
                )
            
            # Check error handling
            health = await manager.get_health_status()
            print(f"Health issues: {health.issues}")
            
    except Exception as e:
        print(f"Expected error during initialization: {e}")


# Example 4: Performance monitoring and alerting
async def example_monitoring_alerting():
    """Example of performance monitoring and alerting."""
    
    config = {
        "collection": {
            "enabled": True,
            "buffer_size": 2000,
            "batch_size": 200
        },
        "storage": {
            "type": "json",
            "directory": "telemetry_data",
            "retention_days": 30
        },
        "alerting": {
            "enabled": True,
            "thresholds": {
                "performance": {
                    "resolution_time_ms": 200,  # Low threshold to trigger alerts
                    "memory_usage_mb": 50,
                    "error_rate_percent": 1.0
                },
                "quality": {
                    "confidence_score": 0.9,  # High threshold
                    "decline_percent": 10.0
                }
            },
            "notifications": {
                "channels": ["log"],
                "rate_limit": {
                    "max_per_hour": 50
                }
            }
        },
        "reporting": {
            "enabled": True,
            "types": ["performance", "health"],
            "schedule": {
                "frequency": "hourly"
            }
        }
    }
    
    async with telemetry_system(config) as manager:
        selector_integration = SelectorTelemetryIntegration()
        
        # Simulate operations that will trigger alerts
        for i in range(20):
            correlation_id = f"alert_test_{i}"
            selector_id = f"slow_selector_{i % 3}"
            
            await selector_integration.start_selector_operation(
                selector_id=selector_id,
                correlation_id=correlation_id,
                strategy="dom_relationship"
            )
            
            # Simulate slow operations that will trigger alerts
            await asyncio.sleep(0.3)  # 300ms > 200ms threshold
            
            # Some operations with low confidence
            confidence = 0.85 if i % 3 == 0 else 0.7  # Some below 0.9 threshold
            
            await selector_integration.record_selector_success(
                selector_id=selector_id,
                correlation_id=correlation_id,
                confidence_score=confidence,
                resolution_time_ms=300,  # Above threshold
                elements_found=1
            )
        
        # Wait for alert processing
        await asyncio.sleep(3)
        
        # Check for alerts
        health = await manager.get_health_status()
        print(f"Alerts triggered: {len(health.issues)}")
        for issue in health.issues:
            print(f"  - {issue}")


# Example 5: Custom integration with existing selector engine
class CustomSelectorEngine:
    """Example of integrating telemetry with an existing selector engine."""
    
    def __init__(self):
        self.telemetry_integration = None
        self.config = {
            "collection": {"enabled": True},
            "storage": {"type": "json", "directory": "custom_telemetry"},
            "alerting": {"enabled": True},
            "reporting": {"enabled": True}
        }
    
    async def initialize(self):
        """Initialize the selector engine with telemetry."""
        manager = get_lifecycle_manager()
        await manager.initialize(self.config)
        await manager.start()
        
        self.telemetry_integration = SelectorTelemetryIntegration()
        print("Custom selector engine initialized with telemetry")
    
    async def resolve_selector(self, 
                              selector_id: str, 
                              strategy: str,
                              context: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve selector with telemetry integration."""
        correlation_id = f"custom_{datetime.now().strftime('%H%M%S')}"
        
        # Start telemetry collection
        await self.telemetry_integration.start_selector_operation(
            selector_id=selector_id,
            correlation_id=correlation_id,
            strategy=strategy
        )
        
        try:
            # Simulate selector resolution
            await asyncio.sleep(0.05)
            
            # Simulate successful resolution
            result = {
                "selector_id": selector_id,
                "elements_found": 2,
                "confidence": 0.88,
                "resolution_time": 50
            }
            
            # Record success with telemetry
            await self.telemetry_integration.record_selector_success(
                selector_id=selector_id,
                correlation_id=correlation_id,
                confidence_score=result["confidence"],
                resolution_time_ms=result["resolution_time"],
                elements_found=result["elements_found"]
            )
            
            return result
            
        except Exception as e:
            # Record error with telemetry
            await self.telemetry_integration.record_selector_error(
                selector_id=selector_id,
                correlation_id=correlation_id,
                error=str(e),
                error_type=type(e).__name__
            )
            raise
    
    async def shutdown(self):
        """Shutdown the selector engine."""
        manager = get_lifecycle_manager()
        await manager.shutdown()


async def example_custom_integration():
    """Example of custom integration with existing selector engine."""
    
    engine = CustomSelectorEngine()
    await engine.initialize()
    
    try:
        # Use the engine with automatic telemetry
        for i in range(10):
            result = await engine.resolve_selector(
                selector_id=f"product_price_{i}",
                strategy="attribute_match",
                context={"page": "product_page"}
            )
            print(f"Resolved selector: {result}")
        
        # Get telemetry summary
        manager = get_lifecycle_manager()
        metrics = await manager.get_system_metrics()
        print(f"Total operations: {metrics.total_operations}")
        print(f"Success rate: {metrics.successful_operations / metrics.total_operations * 100:.1f}%")
        
    finally:
        await engine.shutdown()


# Main function to run examples
async def main():
    """Run all examples."""
    print("=== Telemetry Integration Examples ===\n")
    
    print("1. Basic Integration Example")
    await example_basic_integration()
    print()
    
    print("2. InfluxDB Integration Example")
    await example_influxdb_integration()
    print()
    
    print("3. Error Handling Example")
    await example_error_handling()
    print()
    
    print("4. Monitoring and Alerting Example")
    await example_monitoring_alerting()
    print()
    
    print("5. Custom Integration Example")
    await example_custom_integration()
    print()
    
    print("All examples completed!")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run examples
    asyncio.run(main())
