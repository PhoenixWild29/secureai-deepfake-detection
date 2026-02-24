/**
 * InteractiveConfidenceVisualization Component Export
 * Main export point for the InteractiveConfidenceVisualization component and its utilities
 */

// Main component
export { default as InteractiveConfidenceVisualization } from './InteractiveConfidenceVisualization';
export { CHART_MODES, TREND_TYPES } from './InteractiveConfidenceVisualization';

// Hooks
export { default as useConfidenceChart } from './hooks/useConfidenceChart';

// Services
export { 
  default as confidenceVisualizationDataService,
  ConfidenceVisualizationDataService 
} from './services/confidenceVisualizationDataService';

// Integrations
export { 
  default as frameAnalysisGridIntegration,
  FrameAnalysisGridIntegration 
} from './integrations/frameAnalysisGridIntegration';

export { 
  default as resultExportInterfaceIntegration,
  ResultExportInterfaceIntegration 
} from './integrations/resultExportInterfaceIntegration';

// Types
export * from './types/confidenceVisualization';

// Default export
export { default } from './InteractiveConfidenceVisualization';
