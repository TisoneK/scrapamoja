# Quickstart Guide: Production Resilience & Reliability

**Feature**: 005-production-resilience  
**Date**: 2025-01-27  
**Version**: 1.0.0

## Overview

This guide provides a quick introduction to implementing and using the Production Resilience & Reliability features in the Scorewise scraper. The resilience system provides graceful failure handling, automatic recovery, checkpointing, resource management, and intelligent abort policies.

## Prerequisites

- Python 3.11+ with asyncio
- Playwright (async API)
- psutil for resource monitoring
- Existing browser lifecycle management system
- Structured logging system with correlation IDs

## Basic Setup

### 1. Import Resilience Components

```python
from src.resilience import (
    CheckpointManager,
    RetryManager,
    ResourceMonitor,
    AbortManager,
    FailureHandler,
    ResilienceConfiguration
)
```

### 2. Configure Resilience System

```python
# Basic configuration
config = ResilienceConfiguration(
    checkpoint=CheckpointConfiguration(
        enabled=True,
        interval=300,  # 5 minutes
        retention_count=10,
        compression_enabled=True,
        encryption_enabled=True,
        storage_path="./data/checkpoints",
        validation_enabled=True
    ),
    retry=RetryConfiguration(
        enabled=True,
        default_policy="exponential_backoff",
        max_concurrent_retries=5,
        jitter_enabled=True,
        failure_classification_enabled=True
    ),
    resource=ResourceConfiguration(
        enabled=True,
        monitoring_interval=30,
        default_threshold="production",
        auto_cleanup_enabled=True,
        browser_restart_enabled=True,
        memory_limit_mb=2048,
        cpu_limit_percent=80.0
    ),
    abort=AbortConfiguration(
        enabled=True,
        default_policy="conservative",
        evaluation_interval=60,
        min_operations_before_eval=10,
        abort_notification_enabled=True
    )
)
```

### 3. Initialize Resilience Components

```python
# Initialize managers
checkpoint_manager = CheckpointManager(config.checkpoint)
retry_manager = RetryManager(config.retry)
resource_monitor = ResourceMonitor(config.resource)
abort_manager = AbortManager(config.abort)
failure_handler = FailureHandler()

# Start resource monitoring
monitoring_session = await resource_monitor.start_monitoring(
    threshold_id="production",
    callback=handle_resource_threshold_breach
)
```

## Usage Examples

### Checkpointing

#### Create a Checkpoint

```python
async def create_job_checkpoint(job_id: str, job_state: dict):
    try:
        checkpoint_id = await checkpoint_manager.create_checkpoint(
            job_id=job_id,
            data=job_state,
            metadata={
                "total_items": len(job_state.get("items", [])),
                "completed_items": job_state.get("completed_count", 0),
                "processing_time": time.time() - job_state.get("start_time", time.time())
            }
        )
        print(f"Checkpoint created: {checkpoint_id}")
        return checkpoint_id
    except Exception as e:
        print(f"Checkpoint creation failed: {e}")
        raise
```

#### Resume from Checkpoint

```python
async def resume_from_checkpoint(checkpoint_id: str):
    try:
        checkpoint_data = await checkpoint_manager.load_checkpoint(checkpoint_id)
        if checkpoint_data:
            print(f"Resumed from checkpoint: {checkpoint_id}")
            return checkpoint_data
        else:
            print("Checkpoint not found")
            return None
    except Exception as e:
        print(f"Checkpoint resume failed: {e}")
        raise
```

### Retry Logic

#### Execute Operation with Retry

```python
async def scrape_with_retry(url: str, selector: str):
    async def scrape_operation():
        # Your scraping logic here
        page = await browser.new_page()
        await page.goto(url)
        element = await page.wait_for_selector(selector)
        return await element.text_content()
    
    try:
        result = await retry_manager.execute_with_retry(
            operation=scrape_operation,
            retry_policy_id="exponential_backoff"
        )
        return result
    except MaxRetriesExceededError:
        print("All retry attempts failed")
        raise
    except PermanentFailureError:
        print("Permanent failure detected")
        raise
```

#### Create Custom Retry Policy

```python
async def create_custom_retry_policy():
    policy_config = {
        "name": "aggressive_retry",
        "max_attempts": 10,
        "base_delay": 0.5,
        "multiplier": 1.5,
        "max_delay": 120,
        "jitter_factor": 0.3,
        "failure_classifier": {
            "transient_patterns": [
                r"timeout",
                r"connection.*refused",
                r"rate.*limit"
            ],
            "permanent_patterns": [
                r"404",
                r"403",
                r"authentication.*failed"
            ]
        }
    }
    
    policy_id = await retry_manager.create_retry_policy(policy_config)
    return policy_id
```

### Resource Monitoring

#### Monitor Current Resources

```python
async def check_system_resources():
    metrics = await resource_monitor.get_current_metrics()
    
    print(f"Memory Usage: {metrics['memory_usage']} MB")
    print(f"CPU Usage: {metrics['cpu_usage']}%")
    print(f"Disk Usage: {metrics['disk_usage']} MB")
    print(f"Network Connections: {metrics['network_connections']}")
    
    # Check against thresholds
    threshold_status = await resource_monitor.check_thresholds("production")
    
    for threshold, breached in threshold_status.items():
        if breached:
            print(f"⚠️  Threshold breached: {threshold}")
        else:
            print(f"✅ Threshold OK: {threshold}")
    
    return metrics, threshold_status
```

#### Handle Resource Threshold Breach

```python
async def handle_resource_threshold_breach(threshold_data: dict):
    print(f"Resource threshold breached: {threshold_data}")
    
    if threshold_data.get("memory_percent_breached"):
        print("Memory usage too high, initiating cleanup...")
        # Trigger cleanup actions
        await perform_memory_cleanup()
    
    if threshold_data.get("browser_lifetime_breached"):
        print("Browser lifetime exceeded, restarting...")
        # Restart browser
        await restart_browser_session()
```

### Abort Management

#### Evaluate Abort Conditions

```python
async def check_abort_conditions(job_id: str):
    try:
        evaluation = await abort_manager.evaluate_abort_conditions(
            job_id=job_id,
            abort_policy_id="conservative"
        )
        
        if evaluation["should_abort"]:
            print(f"Job {job_id} should abort: {evaluation['reason']}")
            await abort_manager.execute_abort_actions(
                job_id=job_id,
                abort_reason=evaluation['reason']
            )
        else:
            print(f"Job {job_id} can continue: {evaluation['reason']}")
        
        return evaluation
    except Exception as e:
        print(f"Abort evaluation failed: {e}")
        raise
```

#### Record Failure for Analysis

```python
async def record_scraping_failure(job_id: str, error: Exception, context: dict):
    failure_event = {
        "timestamp": datetime.utcnow(),
        "severity": "error",
        "category": "network",
        "source": "scraper",
        "message": str(error),
        "context": context,
        "stack_trace": traceback.format_exc()
    }
    
    await abort_manager.record_failure(job_id, failure_event)
```

### Failure Handling

#### Handle Failures Automatically

```python
async def handle_scraping_failure(error: Exception, context: dict):
    failure_event = {
        "error_type": type(error).__name__,
        "message": str(error),
        "context": context,
        "timestamp": datetime.utcnow()
    }
    
    try:
        result = await failure_handler.handle_failure(
            failure_event=failure_event,
            context=context
        )
        
        print(f"Failure handled: {result['action_taken']}")
        return result
    except Exception as e:
        print(f"Failure handling failed: {e}")
        raise
```

#### Register Custom Failure Handler

```python
async def register_network_failure_handler():
    async def handle_network_failure(failure_event: dict, context: dict):
        print("Handling network failure...")
        
        # Check if it's a temporary network issue
        if "timeout" in failure_event["message"].lower():
            # Schedule retry with longer delay
            return {
                "action": "retry",
                "delay": 30,
                "reason": "Network timeout detected"
            }
        else:
            return {
                "action": "abort",
                "reason": "Permanent network failure"
            }
    
    await failure_handler.register_failure_handler(
        failure_type="network",
        handler=handle_network_failure
    )
```

## Complete Example

### End-to-End Resilient Scraping Job

```python
import asyncio
import time
from datetime import datetime

class ResilientScraper:
    def __init__(self, config: ResilienceConfiguration):
        self.config = config
        self.checkpoint_manager = CheckpointManager(config.checkpoint)
        self.retry_manager = RetryManager(config.retry)
        self.resource_monitor = ResourceMonitor(config.resource)
        self.abort_manager = AbortManager(config.abort)
        self.failure_handler = FailureHandler()
        
    async def start_resilient_scraping(self, job_id: str, urls: list):
        """Start a resilient scraping job."""
        print(f"Starting resilient scraping job: {job_id}")
        
        # Start resource monitoring
        monitoring_session = await self.resource_monitor.start_monitoring(
            threshold_id="production",
            callback=self.handle_resource_breach
        )
        
        # Check for existing checkpoint
        existing_checkpoint = await self.find_latest_checkpoint(job_id)
        
        if existing_checkpoint:
            print(f"Resuming from checkpoint: {existing_checkpoint}")
            job_state = await self.checkpoint_manager.load_checkpoint(existing_checkpoint)
            start_index = job_state.get("completed_count", 0)
        else:
            job_state = {
                "job_id": job_id,
                "start_time": time.time(),
                "items": urls,
                "completed_count": 0,
                "failed_count": 0,
                "results": []
            }
            start_index = 0
        
        try:
            # Process URLs with resilience
            for i, url in enumerate(urls[start_index:], start_index):
                # Check abort conditions
                abort_eval = await self.abort_manager.evaluate_abort_conditions(
                    job_id=job_id,
                    abort_policy_id="conservative"
                )
                
                if abort_eval["should_abort"]:
                    print(f"Job aborted: {abort_eval['reason']}")
                    break
                
                # Create periodic checkpoint
                if i % 10 == 0:  # Every 10 items
                    await self.create_checkpoint(job_id, job_state)
                
                # Scrape with retry
                try:
                    result = await self.scrape_with_retry(url)
                    job_state["results"].append(result)
                    job_state["completed_count"] += 1
                    print(f"✅ Scraped {i+1}/{len(urls)}: {url}")
                    
                except Exception as e:
                    await self.handle_scraping_failure(e, {"url": url, "index": i})
                    job_state["failed_count"] += 1
                    print(f"❌ Failed {i+1}/{len(urls)}: {url}")
            
            # Final checkpoint
            await self.create_checkpoint(job_id, job_state)
            
            print(f"Job completed: {job_state['completed_count']} successful, {job_state['failed_count']} failed")
            return job_state
            
        except Exception as e:
            print(f"Job failed: {e}")
            # Emergency checkpoint
            await self.create_checkpoint(job_id, job_state)
            raise
            
        finally:
            # Stop monitoring
            await self.resource_monitor.stop_monitoring(monitoring_session)
    
    async def scrape_with_retry(self, url: str):
        """Scrape URL with retry logic."""
        async def scrape_operation():
            # Your scraping logic here
            page = await browser.new_page()
            await page.goto(url)
            # ... scraping logic ...
            return {"url": url, "data": "scraped_data"}
        
        return await self.retry_manager.execute_with_retry(
            operation=scrape_operation,
            retry_policy_id="exponential_backoff"
        )
    
    async def create_checkpoint(self, job_id: str, job_state: dict):
        """Create a checkpoint."""
        await self.checkpoint_manager.create_checkpoint(
            job_id=job_id,
            data=job_state,
            metadata={
                "total_items": len(job_state["items"]),
                "completed_items": job_state["completed_count"],
                "failed_items": job_state["failed_count"],
                "processing_time": time.time() - job_state["start_time"]
            }
        )
    
    async def find_latest_checkpoint(self, job_id: str):
        """Find the latest checkpoint for a job."""
        checkpoints = await self.checkpoint_manager.list_checkpoints(job_id, limit=1)
        return checkpoints[0]["id"] if checkpoints else None
    
    async def handle_resource_breach(self, threshold_data: dict):
        """Handle resource threshold breach."""
        print(f"Resource breach: {threshold_data}")
        
        if threshold_data.get("memory_percent_breached"):
            await self.perform_memory_cleanup()
        
        if threshold_data.get("browser_lifetime_breached"):
            await self.restart_browser()
    
    async def handle_scraping_failure(self, error: Exception, context: dict):
        """Handle scraping failure."""
        failure_event = {
            "error_type": type(error).__name__,
            "message": str(error),
            "context": context,
            "timestamp": datetime.utcnow()
        }
        
        await self.failure_handler.handle_failure(
            failure_event=failure_event,
            context=context
        )
    
    async def perform_memory_cleanup(self):
        """Perform memory cleanup."""
        # Cleanup implementation
        print("Performing memory cleanup...")
    
    async def restart_browser(self):
        """Restart browser."""
        # Browser restart implementation
        print("Restarting browser...")

# Usage
async def main():
    config = ResilienceConfiguration(...)  # Your configuration
    
    scraper = ResilientScraper(config)
    
    urls = [
        "https://example1.com",
        "https://example2.com",
        # ... more URLs
    ]
    
    result = await scraper.start_resilient_scraping("job-123", urls)
    print(f"Scraping result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Examples

### Production Configuration

```python
production_config = ResilienceConfiguration(
    checkpoint=CheckpointConfiguration(
        enabled=True,
        interval=300,  # 5 minutes
        retention_count=20,
        compression_enabled=True,
        encryption_enabled=True,
        storage_path="/data/checkpoints",
        validation_enabled=True
    ),
    retry=RetryConfiguration(
        enabled=True,
        default_policy="conservative",
        max_concurrent_retries=10,
        jitter_enabled=True,
        failure_classification_enabled=True
    ),
    resource=ResourceConfiguration(
        enabled=True,
        monitoring_interval=30,
        default_threshold="production",
        auto_cleanup_enabled=True,
        browser_restart_enabled=True,
        memory_limit_mb=4096,
        cpu_limit_percent=75.0
    ),
    abort=AbortConfiguration(
        enabled=True,
        default_policy="production",
        evaluation_interval=60,
        min_operations_before_eval=20,
        abort_notification_enabled=True
    )
)
```

### Development Configuration

```python
development_config = ResilienceConfiguration(
    checkpoint=CheckpointConfiguration(
        enabled=True,
        interval=60,  # 1 minute
        retention_count=5,
        compression_enabled=False,
        encryption_enabled=False,
        storage_path="./checkpoints",
        validation_enabled=True
    ),
    retry=RetryConfiguration(
        enabled=True,
        default_policy="aggressive",
        max_concurrent_retries=3,
        jitter_enabled=False,
        failure_classification_enabled=True
    ),
    resource=ResourceConfiguration(
        enabled=True,
        monitoring_interval=60,
        default_threshold="development",
        auto_cleanup_enabled=False,
        browser_restart_enabled=False,
        memory_limit_mb=1024,
        cpu_limit_percent=90.0
    ),
    abort=AbortConfiguration(
        enabled=False,  # Disabled in development
        default_policy="development",
        evaluation_interval=300,
        min_operations_before_eval=5,
        abort_notification_enabled=False
    )
)
```

## Troubleshooting

### Common Issues

1. **Checkpoint Creation Fails**
   - Check storage directory permissions
   - Verify disk space availability
   - Ensure data is serializable

2. **Retry Not Working**
   - Verify retry policy configuration
   - Check failure classification patterns
   - Ensure operation is async

3. **Resource Monitoring Not Triggering**
   - Verify threshold configuration
   - Check monitoring callback registration
   - Ensure psutil is installed

4. **Abort Conditions Not Evaluating**
   - Verify abort policy configuration
   - Check failure event recording
   - Ensure minimum operation count reached

### Debug Logging

Enable debug logging for troubleshooting:

```python
import logging

# Set debug level
logging.getLogger("src.resilience").setLevel(logging.DEBUG)

# Enable detailed logging
config.logging.debug_enabled = True
config.logging.include_stack_traces = True
```

## Next Steps

1. **Custom Policies**: Create custom retry, resource, and abort policies for your specific needs
2. **Integration**: Integrate with your existing scraping logic
3. **Monitoring**: Set up monitoring and alerting for resilience events
4. **Testing**: Test resilience features with failure injection
5. **Production Deployment**: Configure production settings and monitoring

For more detailed information, refer to:
- [Data Model Documentation](data-model.md)
- [API Contracts](contracts/resilience-api.md)
- [Research Findings](research.md)
