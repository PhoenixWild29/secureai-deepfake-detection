/**
 * Virtualized Analysis History Widget
 * Efficiently renders large datasets of analysis history with dynamic heights and smooth scrolling
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { FixedSizeList as List, VariableSizeList as VariableList } from 'react-window';
import { measureComponentRender } from '@/utils/performanceMonitor';
import { getApiCache } from '@/services/api';
import styles from './AnalysisHistoryWidget.module.css';

// Types
interface AnalysisItem {
  id: string;
  title: string;
  status: 'completed' | 'processing' | 'failed' | 'pending';
  timestamp: Date;
  duration: number;
  confidence: number;
  fileSize: number;
  fileName: string;
  thumbnail?: string;
  metadata: {
    model: string;
    version: string;
    processingTime: number;
    accuracy: number;
  };
}

interface AnalysisHistoryWidgetProps {
  className?: string;
  height?: number;
  itemHeight?: number;
  enableVirtualization?: boolean;
  enableInfiniteScroll?: boolean;
  enableSearch?: boolean;
  enableFiltering?: boolean;
  enableSorting?: boolean;
  maxItems?: number;
  refreshInterval?: number;
  onItemClick?: (item: AnalysisItem) => void;
  onItemSelect?: (items: AnalysisItem[]) => void;
}

interface VirtualizedItemProps {
  index: number;
  style: React.CSSProperties;
  data: {
    items: AnalysisItem[];
    onItemClick: (item: AnalysisItem) => void;
    onItemSelect: (item: AnalysisItem) => void;
    selectedItems: Set<string>;
    searchQuery: string;
    filterStatus: string;
  };
}

// Analysis item component
const AnalysisItemComponent: React.FC<{
  item: AnalysisItem;
  isSelected: boolean;
  onClick: () => void;
  onSelect: () => void;
}> = ({ item, isSelected, onClick, onSelect }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10b981';
      case 'processing': return '#f59e0b';
      case 'failed': return '#ef4444';
      case 'pending': return '#6b7280';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return '✓';
      case 'processing': return '⏳';
      case 'failed': return '✗';
      case 'pending': return '⏸';
      default: return '?';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div
      className={`${styles.analysisItem} ${isSelected ? styles.selected : ''}`}
      onClick={onClick}
      onMouseDown={(e) => {
        if (e.ctrlKey || e.metaKey) {
          e.preventDefault();
          onSelect();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`Analysis ${item.title}, ${item.status}`}
    >
      <div className={styles.itemHeader}>
        <div className={styles.statusIndicator}>
          <span
            className={styles.statusIcon}
            style={{ color: getStatusColor(item.status) }}
          >
            {getStatusIcon(item.status)}
          </span>
        </div>
        
        <div className={styles.itemInfo}>
          <h3 className={styles.itemTitle}>{item.title}</h3>
          <p className={styles.fileName}>{item.fileName}</p>
        </div>
        
        <div className={styles.itemMeta}>
          <span className={styles.timestamp}>
            {item.timestamp.toLocaleDateString()}
          </span>
          <span className={styles.duration}>
            {formatDuration(item.duration)}
          </span>
        </div>
      </div>
      
      <div className={styles.itemDetails}>
        <div className={styles.confidenceBar}>
          <div className={styles.confidenceLabel}>Confidence:</div>
          <div className={styles.confidenceValue}>
            {(item.confidence * 100).toFixed(1)}%
          </div>
          <div className={styles.confidenceTrack}>
            <div
              className={styles.confidenceFill}
              style={{
                width: `${item.confidence * 100}%`,
                backgroundColor: item.confidence > 0.8 ? '#10b981' : 
                                item.confidence > 0.6 ? '#f59e0b' : '#ef4444'
              }}
            />
          </div>
        </div>
        
        <div className={styles.itemStats}>
          <span className={styles.fileSize}>{formatFileSize(item.fileSize)}</span>
          <span className={styles.model}>{item.metadata.model}</span>
          <span className={styles.accuracy}>
            Accuracy: {(item.metadata.accuracy * 100).toFixed(1)}%
          </span>
        </div>
      </div>
      
      {item.thumbnail && (
        <div className={styles.thumbnail}>
          <img
            src={item.thumbnail}
            alt={`Thumbnail for ${item.title}`}
            className={styles.thumbnailImage}
          />
        </div>
      )}
    </div>
  );
};

// Virtualized item component
const VirtualizedItem: React.FC<VirtualizedItemProps> = ({ index, style, data }) => {
  const { items, onItemClick, onItemSelect, selectedItems, searchQuery, filterStatus } = data;
  const item = items[index];
  
  const isSelected = selectedItems.has(item.id);
  
  const handleClick = useCallback(() => {
    onItemClick(item);
  }, [item, onItemClick]);
  
  const handleSelect = useCallback(() => {
    onItemSelect(item);
  }, [item, onItemSelect]);
  
  return (
    <div style={style}>
      <AnalysisItemComponent
        item={item}
        isSelected={isSelected}
        onClick={handleClick}
        onSelect={handleSelect}
      />
    </div>
  );
};

// Main widget component
export const AnalysisHistoryWidget: React.FC<AnalysisHistoryWidgetProps> = ({
  className = '',
  height = 400,
  itemHeight = 120,
  enableVirtualization = true,
  enableInfiniteScroll = true,
  enableSearch = true,
  enableFiltering = true,
  enableSorting = true,
  maxItems = 1000,
  refreshInterval = 30000,
  onItemClick,
  onItemSelect,
}) => {
  const renderTimer = useRef<{ end: () => number } | null>(null);
  const apiCache = getApiCache();
  
  // State
  const [items, setItems] = useState<AnalysisItem[]>([]);
  const [filteredItems, setFilteredItems] = useState<AnalysisItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [sortBy, setSortBy] = useState<'timestamp' | 'confidence' | 'duration'>('timestamp');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  
  // Refs
  const listRef = useRef<List | VariableList>(null);
  const itemHeightsRef = useRef<Map<number, number>>(new Map());
  
  // Performance monitoring
  useEffect(() => {
    renderTimer.current = measureComponentRender('AnalysisHistoryWidget');
    
    return () => {
      if (renderTimer.current) {
        renderTimer.current.end();
      }
    };
  }, []);
  
  // Load analysis history
  const loadAnalysisHistory = useCallback(async (pageNum: number = 1, append: boolean = false) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiCache.request({
        url: '/api/analysis/history',
        method: 'GET',
        params: {
          page: pageNum,
          limit: 50,
          sortBy,
          sortOrder,
          status: filterStatus === 'all' ? undefined : filterStatus,
          search: searchQuery || undefined,
        },
      });
      
      const newItems: AnalysisItem[] = response.data.map((item: any) => ({
        id: item.id,
        title: item.title,
        status: item.status,
        timestamp: new Date(item.timestamp),
        duration: item.duration,
        confidence: item.confidence,
        fileSize: item.fileSize,
        fileName: item.fileName,
        thumbnail: item.thumbnail,
        metadata: {
          model: item.metadata.model,
          version: item.metadata.version,
          processingTime: item.metadata.processingTime,
          accuracy: item.metadata.accuracy,
        },
      }));
      
      if (append) {
        setItems(prev => [...prev, ...newItems]);
      } else {
        setItems(newItems);
      }
      
      setHasMore(newItems.length === 50);
      setPage(pageNum);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analysis history');
    } finally {
      setLoading(false);
    }
  }, [apiCache, sortBy, sortOrder, filterStatus, searchQuery]);
  
  // Initial load
  useEffect(() => {
    loadAnalysisHistory(1, false);
  }, [loadAnalysisHistory]);
  
  // Auto-refresh
  useEffect(() => {
    if (refreshInterval > 0) {
      const interval = setInterval(() => {
        loadAnalysisHistory(1, false);
      }, refreshInterval);
      
      return () => clearInterval(interval);
    }
  }, [refreshInterval, loadAnalysisHistory]);
  
  // Filter and sort items
  useEffect(() => {
    let filtered = [...items];
    
    // Apply search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(query) ||
        item.fileName.toLowerCase().includes(query) ||
        item.metadata.model.toLowerCase().includes(query)
      );
    }
    
    // Apply status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(item => item.status === filterStatus);
    }
    
    // Apply sorting
    filtered.sort((a, b) => {
      let aValue: any, bValue: any;
      
      switch (sortBy) {
        case 'timestamp':
          aValue = a.timestamp.getTime();
          bValue = b.timestamp.getTime();
          break;
        case 'confidence':
          aValue = a.confidence;
          bValue = b.confidence;
          break;
        case 'duration':
          aValue = a.duration;
          bValue = b.duration;
          break;
        default:
          return 0;
      }
      
      if (sortOrder === 'asc') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    });
    
    setFilteredItems(filtered);
  }, [items, searchQuery, filterStatus, sortBy, sortOrder]);
  
  // Handle item click
  const handleItemClick = useCallback((item: AnalysisItem) => {
    onItemClick?.(item);
  }, [onItemClick]);
  
  // Handle item selection
  const handleItemSelect = useCallback((item: AnalysisItem) => {
    setSelectedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(item.id)) {
        newSet.delete(item.id);
      } else {
        newSet.add(item.id);
      }
      return newSet;
    });
    
    const selectedItemsArray = Array.from(selectedItems).map(id =>
      items.find(item => item.id === id)
    ).filter(Boolean) as AnalysisItem[];
    
    onItemSelect?.(selectedItemsArray);
  }, [onItemClick, selectedItems, items]);
  
  // Handle infinite scroll
  const handleScroll = useCallback(({ scrollTop, scrollHeight, clientHeight }: any) => {
    if (enableInfiniteScroll && hasMore && !loading) {
      const threshold = 100;
      if (scrollTop + clientHeight >= scrollHeight - threshold) {
        loadAnalysisHistory(page + 1, true);
      }
    }
  }, [enableInfiniteScroll, hasMore, loading, page, loadAnalysisHistory]);
  
  // Get item size for variable height virtualization
  const getItemSize = useCallback((index: number) => {
    return itemHeightsRef.current.get(index) || itemHeight;
  }, [itemHeight]);
  
  // Set item size
  const setItemSize = useCallback((index: number, size: number) => {
    itemHeightsRef.current.set(index, size);
    if (listRef.current) {
      (listRef.current as VariableList).resetAfterIndex(index);
    }
  }, []);
  
  // Memoized list data
  const listData = useMemo(() => ({
    items: filteredItems,
    onItemClick: handleItemClick,
    onItemSelect: handleItemSelect,
    selectedItems,
    searchQuery,
    filterStatus,
  }), [filteredItems, handleItemClick, handleItemSelect, selectedItems, searchQuery, filterStatus]);
  
  // Render controls
  const renderControls = () => (
    <div className={styles.controls}>
      {enableSearch && (
        <div className={styles.searchContainer}>
          <input
            type="text"
            placeholder="Search analyses..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={styles.searchInput}
          />
        </div>
      )}
      
      {enableFiltering && (
        <div className={styles.filterContainer}>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className={styles.filterSelect}
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>
      )}
      
      {enableSorting && (
        <div className={styles.sortContainer}>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className={styles.sortSelect}
          >
            <option value="timestamp">Date</option>
            <option value="confidence">Confidence</option>
            <option value="duration">Duration</option>
          </select>
          
          <button
            onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
            className={styles.sortButton}
            aria-label={`Sort ${sortOrder === 'asc' ? 'descending' : 'ascending'}`}
          >
            {sortOrder === 'asc' ? '↑' : '↓'}
          </button>
        </div>
      )}
    </div>
  );
  
  // Render loading state
  if (loading && items.length === 0) {
    return (
      <div className={`${styles.widget} ${className}`}>
        <div className={styles.header}>
          <h2 className={styles.title}>Analysis History</h2>
        </div>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSpinner} />
          <p className={styles.loadingText}>Loading analysis history...</p>
        </div>
      </div>
    );
  }
  
  // Render error state
  if (error) {
    return (
      <div className={`${styles.widget} ${className}`}>
        <div className={styles.header}>
          <h2 className={styles.title}>Analysis History</h2>
        </div>
        <div className={styles.errorContainer}>
          <p className={styles.errorText}>{error}</p>
          <button
            onClick={() => loadAnalysisHistory(1, false)}
            className={styles.retryButton}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }
  
  return (
    <div className={`${styles.widget} ${className}`}>
      <div className={styles.header}>
        <h2 className={styles.title}>Analysis History</h2>
        <div className={styles.stats}>
          {filteredItems.length} of {items.length} analyses
        </div>
      </div>
      
      {renderControls()}
      
      <div className={styles.listContainer} style={{ height }}>
        {enableVirtualization ? (
          <VariableList
            ref={listRef}
            height={height}
            itemCount={filteredItems.length}
            itemSize={getItemSize}
            itemData={listData}
            onScroll={handleScroll}
            overscanCount={5}
          >
            {VirtualizedItem}
          </VariableList>
        ) : (
          <div className={styles.nonVirtualizedList}>
            {filteredItems.map((item, index) => (
              <div key={item.id} style={{ height: itemHeight }}>
                <VirtualizedItem
                  index={index}
                  style={{}}
                  data={listData}
                />
              </div>
            ))}
          </div>
        )}
      </div>
      
      {loading && items.length > 0 && (
        <div className={styles.loadingMore}>
          <div className={styles.loadingSpinner} />
          <span>Loading more...</span>
        </div>
      )}
    </div>
  );
};

export default AnalysisHistoryWidget;
