# InteractiveConfidenceVisualization Component

A comprehensive React component for visualizing confidence scores with interactive charts, trend analysis, and frame-level drill-down capabilities.

## Features

- **Interactive Charts**: Line charts, bar charts, scatter plots with zoom, pan, and tooltips
- **Trend Analysis**: Moving averages, peak/valley detection, statistical overlays
- **Frame Navigation**: Click data points to navigate to specific frames
- **Export Capabilities**: Export chart data in JSON, CSV, PNG, SVG, and PDF formats
- **Real-time Updates**: WebSocket integration for live confidence data
- **Performance Optimized**: Virtualization and caching for large datasets

## Usage

### Basic Usage

```jsx
import React from 'react';
import InteractiveConfidenceVisualization from './InteractiveConfidenceVisualization';

const MyComponent = () => {
  const analysisId = 'analysis_123';
  const frameData = [
    {
      frameNumber: 0,
      confidence: 0.85,
      timestamp: 0.0,
      algorithm: 'ensemble',
      suspiciousRegions: [],
      artifacts: {},
      processingTime: 15
    },
    // ... more frame data
  ];

  const handleFrameSelect = (frameInfo) => {
    console.log('Selected frame:', frameInfo);
    // Navigate to frame in your frame viewer
  };

  const handleDataExport = (data, format) => {
    console.log('Exporting data:', format, data);
    // Handle export (download, save to server, etc.)
  };

  const handleError = (errorType, errorMessage) => {
    console.error('Chart error:', errorType, errorMessage);
    // Handle errors appropriately
  };

  return (
    <InteractiveConfidenceVisualization
      analysisId={analysisId}
      frameData={frameData}
      onFrameSelect={handleFrameSelect}
      onDataExport={handleDataExport}
      onError={handleError}
    />
  );
};
```

### Advanced Configuration

```jsx
const config = {
  // Chart settings
  defaultMode: 'line_chart', // 'line_chart', 'bar_chart', 'scatter_plot', 'heatmap', 'comparative'
  enableZoom: true,
  enablePan: true,
  enableTooltips: true,
  enableAnimation: true,
  
  // Data settings
  frameRate: 30, // FPS for timestamp calculation
  movingAveragePeriod: 10,
  confidenceThresholds: {
    low: 0.0,
    medium: 0.4,
    high: 0.7,
    critical: 0.9
  },
  
  // Performance settings
  enableVirtualization: true,
  maxDataPoints: 1000,
  animationDuration: 300,
  
  // Export settings
  exportFormats: ['json', 'csv', 'png'],
  exportResolution: { width: 1920, height: 1080 }
};

<InteractiveConfidenceVisualization
  analysisId={analysisId}
  frameData={frameData}
  config={config}
  onFrameSelect={handleFrameSelect}
  onDataExport={handleDataExport}
  onError={handleError}
/>
```

## Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `analysisId` | `string` | Yes | Unique identifier for the analysis |
| `frameData` | `Array<ConfidenceDataPoint>` | No | Array of frame confidence data |
| `config` | `ChartConfig` | No | Configuration options to override defaults |
| `onFrameSelect` | `Function` | No | Callback when frame is selected from chart |
| `onDataExport` | `Function` | No | Callback for chart data export |
| `onError` | `Function` | No | Callback for error handling |
| `className` | `string` | No | Additional CSS classes |

## Data Format

### ConfidenceDataPoint

```javascript
{
  frameNumber: 0,           // Frame number (0-based)
  confidence: 0.85,         // Confidence score (0-1)
  timestamp: 0.0,           // Timestamp in seconds
  algorithm: 'ensemble',    // Detection algorithm identifier
  suspiciousRegions: [      // Array of suspicious regions
    {
      regionId: 'region_1',
      coordinates: { x: 100, y: 100, width: 50, height: 50 },
      confidence: 85,
      description: 'Potential face manipulation',
      artifactType: 'face_synthesis',
      severity: 'high'
    }
  ],
  artifacts: {              // Artifact detection data
    compression: 0.2,
    temporal: 0.1,
    spatial: 0.3
  },
  processingTime: 15        // Processing time in milliseconds
}
```

## Integration

### With FrameAnalysisGrid

The component automatically integrates with the existing FrameAnalysisGrid for coordinated navigation:

```jsx
import { frameAnalysisGridIntegration } from './integrations/frameAnalysisGridIntegration';

// Initialize integration
frameAnalysisGridIntegration.initialize(frameAnalysisGridInstance);

// The component will automatically navigate to frames when data points are clicked
```

### With ResultExportInterface

Export functionality integrates with the ResultExportInterface:

```jsx
import { resultExportInterfaceIntegration } from './integrations/resultExportInterfaceIntegration';

// Export data
const exportData = await resultExportInterfaceIntegration.prepareChartData(
  chartData,
  { format: 'json', includeMetadata: true }
);
```

## Styling

The component uses CSS modules for styling. You can override styles by:

1. **CSS Custom Properties**: Override CSS variables
2. **CSS Modules**: Import and extend the module styles
3. **className Prop**: Add custom classes

```css
/* Override default colors */
.interactiveConfidenceVisualization {
  --primary-color: #your-color;
  --secondary-color: #your-color;
}
```

## Performance

- **Virtualization**: Large datasets are automatically virtualized for smooth performance
- **Caching**: Client-side caching reduces data processing overhead
- **Debounced Updates**: Chart updates are debounced to prevent excessive re-renders
- **Canvas Rendering**: Uses HTML5 Canvas for high-performance chart rendering

## Browser Support

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Dependencies

- React 16.8+ (hooks support required)
- No external charting libraries (uses native Canvas API)

## Testing

Run the test component to verify functionality:

```jsx
import InteractiveConfidenceVisualizationTest from './InteractiveConfidenceVisualization.test';

// Use in your app for testing
<InteractiveConfidenceVisualizationTest />
```

## Troubleshooting

### Common Issues

1. **Chart not rendering**: Ensure the container has a defined height
2. **Performance issues**: Enable virtualization for large datasets
3. **Export not working**: Check that the export callback is properly implemented

### Debug Mode

Enable debug information in development:

```jsx
// Debug info will be shown in development mode
process.env.NODE_ENV === 'development'
```
