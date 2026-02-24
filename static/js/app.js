// SecureAI DeepFake Detection - JavaScript Application

class SecureAIApp {
    constructor() {
        this.currentSection = 'single';
        this.analysisHistory = [];
        this.batchFiles = [];
        this.batchResults = [];
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadHistory();
        this.loadStats();
        this.setupCharts();
        this.loadUserProfile();
    }

    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const section = e.target.getAttribute('href').substring(1);
                this.switchSection(section);
            });
        });

        // Single file upload
        this.setupFileUpload();

        // Batch file upload
        this.setupBatchUpload();

        // History search and filters
        this.setupHistoryControls();

        // Modal controls
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });
    }

    switchSection(sectionId) {
        // Update navigation
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('active');
        });
        document.querySelector(`[href="#${sectionId}"]`).classList.add('active');

        // Update sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(sectionId).classList.add('active');

        this.currentSection = sectionId;

        // Update URL hash
        window.location.hash = sectionId;

        // Load section-specific data
        if (sectionId === 'stats') {
            this.loadUserStats();
        } else if (sectionId === 'history') {
            this.loadHistory();
        }
    }

    setupFileUpload() {
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');

        // Click to upload
        uploadZone.addEventListener('click', () => {
            fileInput.click();
        });

        // Drag and drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => {
                uploadZone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => {
                uploadZone.classList.remove('dragover');
            });
        });

        uploadZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileUpload(e.target.files[0]);
            }
        });
    }

    setupBatchUpload() {
        const batchUploadZone = document.getElementById('batchUploadZone');
        const batchFileInput = document.getElementById('batchFileInput');

        batchUploadZone.addEventListener('click', () => {
            batchFileInput.click();
        });

        batchFileInput.addEventListener('change', (e) => {
            this.handleBatchFiles(e.target.files);
        });

        // Batch controls
        document.getElementById('startBatchBtn').addEventListener('click', () => {
            this.startBatchAnalysis();
        });

        document.getElementById('clearBatchBtn').addEventListener('click', () => {
            this.clearBatchFiles();
        });
    }

    setupHistoryControls() {
        const searchInput = document.getElementById('historySearch');

        searchInput.addEventListener('input', (e) => {
            this.filterHistory(e.target.value);
        });

        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.filterHistoryByType(e.target.dataset.filter);
            });
        });
    }

    async handleFileUpload(file) {
        if (!this.validateFile(file)) return;

        try {
            // Show upload progress
            this.showUploadProgress();

            // Upload file
            const formData = new FormData();
            formData.append('video', file);

            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('Upload failed');
            }

            const uploadData = await uploadResponse.json();
            const videoId = uploadData.video_id;

            // Show analysis modal
            this.showAnalysisModal();

            // Start analysis
            await this.analyzeVideo(videoId, file.name);

        } catch (error) {
            console.error('Upload error:', error);
            this.showError('Failed to upload video. Please try again.');
        }
    }

    async analyzeVideo(videoId, filename) {
        try {
            this.updateAnalysisProgress(10, 'Initializing analysis...');

            const response = await fetch(`/api/analyze/${videoId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            this.updateAnalysisProgress(50, 'Processing video...');

            const result = await response.json();

            this.updateAnalysisProgress(100, 'Analysis complete!');

            // Hide modal after a moment
            setTimeout(() => {
                this.hideAnalysisModal();
                this.displayResults(result, filename);
            }, 1000);

        } catch (error) {
            console.error('Analysis error:', error);
            this.showError('Analysis failed. Please try again.');
            this.hideAnalysisModal();
        }
    }

    displayResults(result, filename) {
        const resultsContainer = document.getElementById('resultsContainer');
        const resultStatus = document.getElementById('resultStatus');

        // Update status
        resultStatus.className = 'result-status ' + (result.is_fake ? 'fake' : 'authentic');
        resultStatus.innerHTML = `
            <i class="fas ${result.is_fake ? 'fa-exclamation-triangle' : 'fa-shield-alt'}"></i>
            ${result.is_fake ? 'FAKE DETECTED' : 'AUTHENTIC'}
        `;

        // Update metrics
        document.getElementById('authenticityScore').textContent = result.authenticity_score;
        document.getElementById('confidenceScore').textContent = `${(result.confidence * 100).toFixed(1)}%`;
        document.getElementById('videoHash').textContent = result.video_hash.substring(0, 16) + '...';
        document.getElementById('processingTime').textContent = result.analysis_time;

        // Update analysis details
        this.displayAnalysisDetails(result.details);

        // Show blockchain info if available
        if (result.blockchain_tx) {
            document.getElementById('blockchainInfo').style.display = 'block';
            document.getElementById('transactionHash').textContent = result.blockchain_tx;
        }

        // Show storage status
        this.displayStorageStatus(result.storage);

        // Show results
        resultsContainer.style.display = 'block';
        resultsContainer.scrollIntoView({ behavior: 'smooth' });

        // Save to history
        this.saveToHistory(result, filename);
    }

    displayAnalysisDetails(details) {
        const detailsGrid = document.getElementById('analysisDetails');
        detailsGrid.innerHTML = '';

        const detailLabels = {
            frame_consistency: 'Frame Consistency',
            motion_patterns: 'Motion Patterns',
            color_distribution: 'Color Distribution',
            compression_artifacts: 'Compression Artifacts',
            temporal_consistency: 'Temporal Consistency',
            face_detection: 'Face Detection'
        };

        Object.entries(details).forEach(([key, value]) => {
            const detailItem = document.createElement('div');
            detailItem.className = 'detail-item';
            detailItem.innerHTML = `
                <span class="detail-label">${detailLabels[key] || key}</span>
                <span class="detail-value">${(value * 100).toFixed(1)}%</span>
            `;
            detailsGrid.appendChild(detailItem);
        });
    }

    displayStorageStatus(storage) {
        const storageStatus = document.getElementById('storageStatus');
        storageStatus.innerHTML = '';

        const storageIndicator = storage === 's3'
            ? '<span class="storage-indicator cloud"><i class="fas fa-cloud"></i> Stored in Cloud</span>'
            : '<span class="storage-indicator"><i class="fas fa-server"></i> Stored Locally</span>';

        storageStatus.innerHTML = `
            <strong>Storage Status:</strong> ${storageIndicator}
        `;
    }

    handleBatchFiles(files) {
        this.batchFiles = Array.from(files).filter(file => this.validateFile(file));

        if (this.batchFiles.length > 0) {
            document.getElementById('startBatchBtn').disabled = false;
            this.displayBatchQueue();
        }
    }

    displayBatchQueue() {
        const queueContainer = document.getElementById('batchQueue');
        const queueList = document.getElementById('queueList');

        queueList.innerHTML = '';
        this.batchFiles.forEach((file, index) => {
            const queueItem = document.createElement('div');
            queueItem.className = 'queue-item';
            queueItem.innerHTML = `
                <div class="queue-info">
                    <span class="queue-name">${file.name}</span>
                    <span class="queue-size">${this.formatFileSize(file.size)}</span>
                </div>
                <div class="queue-status" id="queue-status-${index}">
                    <i class="fas fa-clock"></i> Waiting
                </div>
            `;
            queueList.appendChild(queueItem);
        });

        queueContainer.style.display = 'block';
    }

    async startBatchAnalysis() {
        const batchResults = document.getElementById('batchResults');
        const resultsTableBody = document.getElementById('resultsTableBody');

        batchResults.style.display = 'block';
        resultsTableBody.innerHTML = '';

        let totalProcessed = 0;
        let authenticCount = 0;
        let fakeCount = 0;
        let totalTime = 0;

        for (let i = 0; i < this.batchFiles.length; i++) {
            const file = this.batchFiles[i];
            const statusElement = document.getElementById(`queue-status-${i}`);

            try {
                statusElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

                // Upload file
                const formData = new FormData();
                formData.append('video', file);

                const uploadResponse = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!uploadResponse.ok) throw new Error('Upload failed');

                const uploadData = await uploadResponse.json();
                const videoId = uploadData.video_id;

                // Analyze
                const analysisResponse = await fetch(`/api/analyze/${videoId}`, {
                    method: 'POST'
                });

                if (!analysisResponse.ok) throw new Error('Analysis failed');

                const result = await analysisResponse.json();

                // Update counters
                totalProcessed++;
                if (result.is_fake) fakeCount++;
                else authenticCount++;
                totalTime += parseFloat(result.analysis_time);

                // Update status
                statusElement.innerHTML = '<i class="fas fa-check"></i> Complete';
                statusElement.style.color = 'var(--secondary-color)';

                // Add to results table
                this.addBatchResultRow(result, file.name);

                // Update summary
                this.updateBatchSummary(totalProcessed, authenticCount, fakeCount, totalTime / totalProcessed);

            } catch (error) {
                console.error(`Batch analysis error for ${file.name}:`, error);
                statusElement.innerHTML = '<i class="fas fa-times"></i> Failed';
                statusElement.style.color = 'var(--danger-color)';
            }
        }

        // Save batch results
        this.saveBatchResults();
    }

    addBatchResultRow(result, filename) {
        const resultsTableBody = document.getElementById('resultsTableBody');
        const row = document.createElement('tr');

        row.innerHTML = `
            <td>${filename}</td>
            <td>
                <span class="result-status ${result.is_fake ? 'fake' : 'authentic'}">
                    ${result.is_fake ? 'Fake' : 'Authentic'}
                </span>
            </td>
            <td>${(result.confidence * 100).toFixed(1)}%</td>
            <td>${result.analysis_time}</td>
            <td>
                <button class="btn btn-secondary btn-sm" onclick="app.viewResult('${result.video_hash}')">
                    <i class="fas fa-eye"></i> View
                </button>
            </td>
        `;

        resultsTableBody.appendChild(row);
    }

    updateBatchSummary(total, authentic, fake, avgTime) {
        document.getElementById('totalProcessed').textContent = total;
        document.getElementById('authenticCount').textContent = authentic;
        document.getElementById('fakeCount').textContent = fake;
        document.getElementById('avgTime').textContent = `${avgTime.toFixed(2)}s`;
    }

    clearBatchFiles() {
        this.batchFiles = [];
        document.getElementById('batchQueue').style.display = 'none';
        document.getElementById('batchResults').style.display = 'none';
        document.getElementById('startBatchBtn').disabled = true;
        document.getElementById('batchFileInput').value = '';
    }

    saveToHistory(result, filename) {
        const historyItem = {
            id: Date.now(),
            filename: filename,
            result: result,
            timestamp: new Date().toISOString()
        };

        this.analysisHistory.unshift(historyItem);
        localStorage.setItem('secureai_history', JSON.stringify(this.analysisHistory.slice(0, 100))); // Keep last 100

        this.updateHistoryDisplay();
        this.updateStats();
    }

    saveBatchResults() {
        const batchData = {
            id: Date.now(),
            files: this.batchFiles.map(f => f.name),
            results: this.batchResults,
            timestamp: new Date().toISOString()
        };

        // Save to localStorage for now (in production, this would go to a database)
        const batches = JSON.parse(localStorage.getItem('secureai_batches') || '[]');
        batches.unshift(batchData);
        localStorage.setItem('secureai_batches', JSON.stringify(batches.slice(0, 50))); // Keep last 50 batches
    }

    loadHistory() {
        const history = localStorage.getItem('secureai_history');
        if (history) {
            this.analysisHistory = JSON.parse(history);
            this.updateHistoryDisplay();
        }
    }

    updateHistoryDisplay() {
        const historyList = document.getElementById('historyList');
        historyList.innerHTML = '';

        this.analysisHistory.forEach(item => {
            const historyItem = document.createElement('div');
            historyItem.className = 'history-item';

            const date = new Date(item.timestamp).toLocaleString();

            historyItem.innerHTML = `
                <div class="history-info">
                    <h4>${item.filename}</h4>
                    <div class="history-meta">
                        <span>${date}</span>
                        <span>Score: ${item.result.authenticity_score}</span>
                    </div>
                </div>
                <div class="history-status ${item.result.is_fake ? 'fake' : 'authentic'}">
                    ${item.result.is_fake ? 'Fake' : 'Authentic'}
                </div>
            `;

            historyList.appendChild(historyItem);
        });
    }

    filterHistory(query) {
        const items = document.querySelectorAll('.history-item');
        items.forEach(item => {
            const filename = item.querySelector('h4').textContent.toLowerCase();
            const visible = filename.includes(query.toLowerCase());
            item.style.display = visible ? 'flex' : 'none';
        });
    }

    filterHistoryByType(type) {
        const items = document.querySelectorAll('.history-item');
        items.forEach(item => {
            const status = item.querySelector('.history-status').classList.contains('fake') ? 'fake' : 'authentic';
            const visible = type === 'all' || status === type;
            item.style.display = visible ? 'flex' : 'none';
        });
    }

    loadStats() {
        // Load stats from API or localStorage
        this.updateStats();
    }

    async loadUserStats() {
        try {
            const response = await fetch('/api/user/stats');
            if (response.ok) {
                const stats = await response.json();

                document.getElementById('total-videos').textContent = stats.total_analyses;
                document.getElementById('fake-count').textContent = stats.fake_detected;
                document.getElementById('authentic-count').textContent = stats.authentic_detected;
                document.getElementById('avg-time').textContent = 'Loading...';

                // Update charts with user data
                this.updateCharts(stats);
            }
        } catch (error) {
            console.error('Failed to load user stats:', error);
        }

        // Load advanced analytics
        await this.loadAdvancedAnalytics();

        // Also load storage status
        await this.loadStorageStatus();
    }

    // Load advanced analytics with insights
    async loadAdvancedAnalytics() {
        try {
            const response = await fetch('/api/analytics/advanced');
            if (response.ok) {
                const analytics = await response.json();

                // Update average time
                document.getElementById('avg-time').textContent = `${analytics.performance.avg_processing_time.toFixed(1)}s`;

                // Display insights
                this.displayInsights(analytics.insights);

                // Display recommendations
                this.displayRecommendations(analytics.recommendations);

                // Update charts with advanced data
                this.updateAdvancedCharts(analytics);
            }
        } catch (error) {
            console.error('Failed to load advanced analytics:', error);
        }
    }

    // Display AI insights
    displayInsights(insights) {
        const insightsGrid = document.getElementById('insights-grid');

        if (insights.length === 0) {
            insightsGrid.innerHTML = '<p class="no-insights">Analyze more videos to generate insights</p>';
            return;
        }

        const insightsHtml = insights.map(insight => `
            <div class="insight-card ${insight.trend}">
                <div class="insight-icon">
                    <i class="fas ${this.getInsightIcon(insight.type)}"></i>
                </div>
                <div class="insight-content">
                    <h4>${insight.title}</h4>
                    <p>${insight.message}</p>
                    ${insight.value !== undefined ? `<div class="insight-value">${insight.value}</div>` : ''}
                </div>
            </div>
        `).join('');

        insightsGrid.innerHTML = insightsHtml;
    }

    // Display recommendations
    displayRecommendations(recommendations) {
        const recommendationsSection = document.getElementById('recommendations-section');
        const recommendationsList = document.getElementById('recommendations-list');

        if (recommendations.length === 0) {
            recommendationsSection.style.display = 'none';
            return;
        }

        recommendationsSection.style.display = 'block';

        const recommendationsHtml = recommendations.map(rec => `
            <div class="recommendation-card ${rec.priority}">
                <div class="recommendation-header">
                    <span class="priority-badge ${rec.priority}">${rec.priority.toUpperCase()}</span>
                    <h4>${rec.title}</h4>
                </div>
                <p>${rec.message}</p>
                <div class="recommendation-action">${rec.action}</div>
            </div>
        `).join('');

        recommendationsList.innerHTML = recommendationsHtml;
    }

    // Get icon for insight type
    getInsightIcon(type) {
        const icons = {
            'performance': 'fa-tachometer-alt',
            'detection': 'fa-search',
            'accuracy': 'fa-bullseye',
            'usage': 'fa-chart-line',
            'storage': 'fa-database'
        };
        return icons[type] || 'fa-info-circle';
    }

    setupCharts() {
        // Initialize Chart.js charts
        this.trendsChart = new Chart(document.getElementById('trendsChart'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Analyses',
                    data: [],
                    borderColor: 'var(--primary-color)',
                    backgroundColor: 'rgba(99, 102, 241, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });

        this.distributionChart = new Chart(document.getElementById('distributionChart'), {
            type: 'doughnut',
            data: {
                labels: ['Authentic', 'Fake'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['var(--secondary-color)', 'var(--danger-color)'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { position: 'bottom' }
                }
            }
        });
    }

    updateCharts(stats) {
        // Results distribution chart
        const resultsCtx = document.getElementById('results-chart').getContext('2d');
        new Chart(resultsCtx, {
            type: 'doughnut',
            data: {
                labels: ['Authentic Videos', 'Deepfakes Detected'],
                datasets: [{
                    data: [stats.authentic_detected, stats.fake_detected],
                    backgroundColor: ['#28a745', '#dc3545'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        // Processing time chart (simplified for now)
        const timeCtx = document.getElementById('time-chart').getContext('2d');
        new Chart(timeCtx, {
            type: 'bar',
            data: {
                labels: ['Your Analyses'],
                datasets: [{
                    label: 'Total Analyses',
                    data: [stats.total_analyses],
                    backgroundColor: '#667eea'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }

    // Update charts with advanced analytics data
    updateAdvancedCharts(analytics) {
        // Enhanced processing time chart
        const timeCtx = document.getElementById('time-chart').getContext('2d');
        new Chart(timeCtx, {
            type: 'line',
            data: {
                labels: analytics.performance.processing_times.map((_, i) => `Analysis ${i + 1}`),
                datasets: [{
                    label: 'Processing Time (seconds)',
                    data: analytics.performance.processing_times,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Time (seconds)'
                        }
                    }
                }
            }
        });

        // Add confidence distribution chart if we have space
        if (analytics.performance.confidence_distribution.fake.length > 0 ||
            analytics.performance.confidence_distribution.authentic.length > 0) {

            // Create new chart container for confidence
            const chartsContainer = document.querySelector('.charts-container');
            const confidenceCard = document.createElement('div');
            confidenceCard.className = 'chart-card';
            confidenceCard.innerHTML = `
                <h3>Detection Confidence Distribution</h3>
                <canvas id="confidence-chart"></canvas>
            `;

            // Insert after the time chart
            const timeChartCard = chartsContainer.querySelectorAll('.chart-card')[1];
            timeChartCard.parentNode.insertBefore(confidenceCard, timeChartCard.nextSibling);

            const confidenceCtx = document.getElementById('confidence-chart').getContext('2d');
            const datasets = [];

            if (analytics.performance.confidence_distribution.fake.length > 0) {
                datasets.push({
                    label: 'Fake Videos',
                    data: analytics.performance.confidence_distribution.fake.map(c => c * 100),
                    backgroundColor: 'rgba(220, 53, 69, 0.7)',
                    borderColor: '#dc3545',
                    borderWidth: 1
                });
            }

            if (analytics.performance.confidence_distribution.authentic.length > 0) {
                datasets.push({
                    label: 'Authentic Videos',
                    data: analytics.performance.confidence_distribution.authentic.map(c => c * 100),
                    backgroundColor: 'rgba(40, 167, 69, 0.7)',
                    borderColor: '#28a745',
                    borderWidth: 1
                });
            }

            new Chart(confidenceCtx, {
                type: 'boxplot',
                data: {
                    labels: ['Confidence Scores'],
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            title: {
                                display: true,
                                text: 'Confidence (%)'
                           