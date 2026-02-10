# Selector Telemetry Dashboard

This directory contains dashboard templates for monitoring the selector telemetry system.

## Files

- `index.html` - Main dashboard with real-time metrics, charts, and alerts
- `config.json` - Dashboard configuration (API endpoints, refresh intervals, etc.)

## Features

### Real-time Metrics
- Total operations count
- Average resolution time
- Success rate and error rate
- Average confidence scores
- Memory usage
- Throughput measurements
- Active selector count

### Interactive Charts
- **Performance Trends**: Resolution time and throughput over time
- **Selector Usage Distribution**: Most frequently used selectors
- **Confidence Score Distribution**: Histogram of confidence scores
- **Error Rate Trends**: Error rate over time

### Alert System
- Real-time alert display
- Severity-based color coding (critical, warning, info)
- Timestamp and detailed messages
- Automatic refresh

### Time Range Selection
- Last hour
- Last 6 hours  
- Last 24 hours
- Last 7 days
- Last 30 days

## Configuration

The dashboard can be configured by modifying the `config.json` file:

```json
{
  "api": {
    "baseUrl": "http://localhost:8080/api/telemetry",
    "endpoints": {
      "metrics": "/metrics",
      "performance": "/performance",
      "alerts": "/alerts"
    }
  },
  "refresh": {
    "interval": 30000,
    "autoRefresh": true
  },
  "charts": {
    "maxDataPoints": 100,
    "animationDuration": 1000
  }
}
```

## Integration

### API Endpoints

The dashboard expects the following API endpoints:

#### GET `/api/telemetry/metrics`
Returns current system metrics:
```json
{
  "totalOperations": 125000,
  "averageResolutionTime": 75.2,
  "successRate": 0.95,
  "errorRate": 0.02,
  "averageConfidence": 0.87,
  "memoryUsage": 125.5,
  "throughput": 850.0,
  "activeSelectors": 45
}
```

#### GET `/api/telemetry/performance?timeRange=24h`
Returns performance time series data:
```json
{
  "performanceData": [
    {
      "time": "2025-01-27T10:00:00Z",
      "resolutionTime": 65.2,
      "throughput": 920.5
    }
  ],
  "errorData": [
    {
      "time": "2025-01-27T10:00:00Z", 
      "errorRate": 0.015
    }
  ]
}
```

#### GET `/api/telemetry/usage?timeRange=24h`
Returns selector usage distribution:
```json
{
  "usageData": [
    {
      "selector": "product_title",
      "count": 1250
    }
  ],
  "confidenceData": [
    {
      "range": "0.9-1.0",
      "count": 2100
    }
  ]
}
```

#### GET `/api/telemetry/alerts?timeRange=24h`
Returns recent alerts:
```json
{
  "alerts": [
    {
      "severity": "warning",
      "title": "High Resolution Time",
      "message": "Selector resolution exceeded threshold",
      "time": "2025-01-27T10:30:00Z"
    }
  ]
}
```

### Customization

#### Adding New Metrics
1. Update the API endpoint to include the new metric
2. Add the metric to the `updateMetrics()` function in `index.html`
3. Add corresponding CSS styling if needed

#### Adding New Charts
1. Add a new canvas element in the charts grid
2. Create a new chart update function
3. Call the function from `updateCharts()`

#### Custom Styling
The dashboard uses CSS custom properties for easy theming:

```css
:root {
  --primary-color: #667eea;
  --secondary-color: #764ba2;
  --success-color: #28a745;
  --warning-color: #ffc107;
  --error-color: #dc3545;
  --background-color: #f8f9fa;
  --card-background: #ffffff;
}
```

## Deployment

### Local Development
1. Start the telemetry API server
2. Open `index.html` in a web browser
3. The dashboard will automatically connect to the local API

### Production Deployment
1. Host the dashboard files on a web server
2. Update the API base URL in `config.json`
3. Configure CORS on the API server if needed
4. Set up authentication if required

### Docker Deployment
```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/
COPY config.json /usr/share/nginx/html/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## Security Considerations

- The dashboard should be served over HTTPS in production
- Implement authentication for sensitive data
- Configure CORS properly for API access
- Consider rate limiting for dashboard refresh requests
- Sanitize all data displayed in the dashboard

## Performance Optimization

- Use server-side aggregation for large datasets
- Implement caching for frequently accessed metrics
- Consider WebSocket connections for real-time updates
- Optimize chart rendering for mobile devices
- Use CDN for static assets in production

## Troubleshooting

### Common Issues

1. **Dashboard shows no data**
   - Check API server is running
   - Verify API endpoints are accessible
   - Check browser console for JavaScript errors

2. **Charts not rendering**
   - Ensure Chart.js library is loaded
   - Check data format matches expected structure
   - Verify canvas elements exist in DOM

3. **Slow loading**
   - Reduce time range for large datasets
   - Implement server-side pagination
   - Optimize API response times

4. **Auto-refresh not working**
   - Check JavaScript interval is set correctly
   - Verify network connectivity to API
   - Look for browser console errors

### Debug Mode
Add `?debug=true` to the URL to enable debug logging:
```javascript
const debug = new URLSearchParams(window.location.search).get('debug') === 'true';
if (debug) {
    console.log('Debug mode enabled');
}
```

## Browser Compatibility

The dashboard supports:
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

For older browsers, consider using polyfills for:
- Fetch API
- Promise
- Arrow functions
- Template literals
