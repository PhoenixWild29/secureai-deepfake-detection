/**
 * Dashboard Page
 * Main dashboard page integrating the video upload component with existing functionality
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import VideoUploadComponent from '../components/VideoUpload/VideoUploadComponent';
import './Dashboard.css';

/**
 * Dashboard component
 * @returns {JSX.Element} Dashboard page
 */
const Dashboard = () => {
  // Authentication hook
  const { user, isAuthenticated, isLoading, signOut } = useAuth();

  // Component state
  const [activeTab, setActiveTab] = useState('upload');
  const [uploadHistory, setUploadHistory] = useState([]);
  const [analysisResults, setAnalysisResults] = useState([]);
  const [systemStats, setSystemStats] = useState({
    totalUploads: 0,
    totalAnalyses: 0,
    successRate: 0,
    avgProcessingTime: 0
  });

  // Load dashboard data on mount
  useEffect(() => {
    if (isAuthenticated) {
      loadDashboardData();
    }
  }, [isAuthenticated]);

  /**
   * Load dashboard data from API
   */
  const loadDashboardData = async () => {
    try {
      // Load upload history
      const historyResponse = await fetch('/api/uploads/history', {
        credentials: 'include'
      });
      if (historyResponse.ok) {
        const historyData = await historyResponse.json();
        setUploadHistory(historyData.uploads || []);
      }

      // Load analysis results
      const resultsResponse = await fetch('/api/analyses/results', {
        credentials: 'include'
      });
      if (resultsResponse.ok) {
        const resultsData = await resultsResponse.json();
        setAnalysisResults(resultsData.results || []);
      }

      // Load system statistics
      const statsResponse = await fetch('/api/stats', {
        credentials: 'include'
      });
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setSystemStats(statsData);
      }
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    }
  };

  /**
   * Handle successful video upload
   * @param {Object} result - Upload result
   * @param {Object} fileData - File data
   */
  const handleUploadComplete = (result, fileData) => {
    console.log('Upload completed:', result);
    
    // Add to upload history
    const newUpload = {
      id: result.video_id,
      filename: fileData.metadata?.name || 'Unknown',
      size: fileData.metadata?.size || 0,
      uploadDate: new Date().toISOString(),
      status: 'uploaded',
      thumbnail: fileData.preview
    };
    
    setUploadHistory(prev => [newUpload, ...prev]);
    
    // Update system stats
    setSystemStats(prev => ({
      ...prev,
      totalUploads: prev.totalUploads + 1
    }));

    // Show success message
    alert(`Video uploaded successfully! Video ID: ${result.video_id}`);
  };

  /**
   * Handle upload error
   * @param {string} error - Error message
   */
  const handleUploadError = (error) => {
    console.error('Upload error:', error);
    alert(`Upload failed: ${error}`);
  };

  /**
   * Handle file selection
   * @param {File} file - Selected file
   * @param {Object} fileData - File data
   */
  const handleFileSelect = (file, fileData) => {
    console.log('File selected:', file, fileData);
  };

  /**
   * Handle user logout
   */
  const handleLogout = async () => {
    try {
      await signOut();
      window.location.href = '/login';
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  /**
   * Format file size for display
   * @param {number} bytes - File size in bytes
   * @returns {string} Formatted file size
   */
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  /**
   * Format date for display
   * @param {string} dateString - ISO date string
   * @returns {string} Formatted date
   */
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Show loading state
  if (isLoading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  // Show authentication required
  if (!isAuthenticated) {
    return (
      <div className="dashboard-auth-required">
        <h2>Authentication Required</h2>
        <p>Please log in to access the dashboard.</p>
        <button onClick={() => window.location.href = '/login'}>
          Go to Login
        </button>
      </div>
    );
  }

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-content">
          <div className="header-left">
            <h1>SecureAI Dashboard</h1>
            <p>Welcome back, {user?.name || user?.email || 'User'}!</p>
          </div>
          <div className="header-right">
            <div className="user-info">
              <span className="user-avatar">
                {(user?.name || user?.email || 'U').charAt(0).toUpperCase()}
              </span>
              <div className="user-details">
                <span className="user-name">{user?.name || 'User'}</span>
                <span className="user-email">{user?.email}</span>
              </div>
            </div>
            <button className="logout-button" onClick={handleLogout}>
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="dashboard-nav">
        <button
          className={`nav-tab ${activeTab === 'upload' ? 'active' : ''}`}
          onClick={() => setActiveTab('upload')}
        >
          📹 Upload Video
        </button>
        <button
          className={`nav-tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📋 Upload History
        </button>
        <button
          className={`nav-tab ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          🔍 Analysis Results
        </button>
        <button
          className={`nav-tab ${activeTab === 'stats' ? 'active' : ''}`}
          onClick={() => setActiveTab('stats')}
        >
          📊 Statistics
        </button>
      </nav>

      {/* Main Content */}
      <main className="dashboard-content">
        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div className="tab-content upload-tab">
            <div className="tab-header">
              <h2>Upload Video for Analysis</h2>
              <p>Upload your video file for deepfake detection analysis</p>
            </div>
            <VideoUploadComponent
              onUploadComplete={handleUploadComplete}
              onUploadError={handleUploadError}
              onFileSelect={handleFileSelect}
              options={{
                userId: user?.id,
                metadata: {
                  source: 'dashboard',
                  userAgent: navigator.userAgent
                }
              }}
            />
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="tab-content history-tab">
            <div className="tab-header">
              <h2>Upload History</h2>
              <p>View your recent video uploads</p>
            </div>
            <div className="upload-history">
              {uploadHistory.length === 0 ? (
                <div className="empty-state">
                  <p>No uploads found. Upload your first video to get started!</p>
                </div>
              ) : (
                <div className="history-list">
                  {uploadHistory.map((upload) => (
                    <div key={upload.id} className="history-item">
                      {upload.thumbnail && (
                        <img
                          src={upload.thumbnail}
                          alt="Video thumbnail"
                          className="history-thumbnail"
                        />
                      )}
                      <div className="history-details">
                        <h4 className="history-filename">{upload.filename}</h4>
                        <div className="history-meta">
                          <span>Size: {formatFileSize(upload.size)}</span>
                          <span>Uploaded: {formatDate(upload.uploadDate)}</span>
                          <span className={`status ${upload.status}`}>
                            {upload.status}
                          </span>
                        </div>
                      </div>
                      <div className="history-actions">
                        <button className="action-button primary">
                          Analyze
                        </button>
                        <button className="action-button secondary">
                          Download
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Results Tab */}
        {activeTab === 'results' && (
          <div className="tab-content results-tab">
            <div className="tab-header">
              <h2>Analysis Results</h2>
              <p>View results from your video analyses</p>
            </div>
            <div className="analysis-results">
              {analysisResults.length === 0 ? (
                <div className="empty-state">
                  <p>No analysis results found. Upload and analyze a video to see results!</p>
                </div>
              ) : (
                <div className="results-list">
                  {analysisResults.map((result) => (
                    <div key={result.id} className="result-item">
                      <div className="result-header">
                        <h4 className="result-filename">{result.filename}</h4>
                        <span className={`result-status ${result.status}`}>
                          {result.status}
                        </span>
                      </div>
                      <div className="result-details">
                        <div className="result-confidence">
                          <span>Confidence: {result.confidence}%</span>
                          <div className="confidence-bar">
                            <div
                              className="confidence-fill"
                              style={{ width: `${result.confidence}%` }}
                            />
                          </div>
                        </div>
                        <div className="result-meta">
                          <span>Analysis Date: {formatDate(result.analysisDate)}</span>
                          <span>Processing Time: {result.processingTime}s</span>
                        </div>
                      </div>
                      <div className="result-actions">
                        <button className="action-button primary">
                          View Details
                        </button>
                        <button className="action-button secondary">
                          Download Report
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Stats Tab */}
        {activeTab === 'stats' && (
          <div className="tab-content stats-tab">
            <div className="tab-header">
              <h2>System Statistics</h2>
              <p>Overview of your usage and system performance</p>
            </div>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon">📹</div>
                <div className="stat-content">
                  <h3>{systemStats.totalUploads}</h3>
                  <p>Total Uploads</p>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">🔍</div>
                <div className="stat-content">
                  <h3>{systemStats.totalAnalyses}</h3>
                  <p>Analyses Completed</p>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">✅</div>
                <div className="stat-content">
                  <h3>{systemStats.successRate}%</h3>
                  <p>Success Rate</p>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon">⏱️</div>
                <div className="stat-content">
                  <h3>{systemStats.avgProcessingTime}s</h3>
                  <p>Avg Processing Time</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
