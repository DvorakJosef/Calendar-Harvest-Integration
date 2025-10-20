/**
 * Calendar to Harvest Integration - Main JavaScript
 */

// Global app object
const CalendarHarvestApp = {
    // Configuration
    config: {
        apiBaseUrl: '/api',
        dateFormat: 'YYYY-MM-DD',
        timeFormat: 'HH:mm'
    },

    // Calendar label colors (matching Google Calendar)
    labelColors: {
        'Finshape': '#7ae7bf',          // Sage (light green)
        'Osobní': '#dbadff',            // Grape (purple)
        'Grada': '#ff887c',             // Flamingo (light orange)
        'ČSAS Promise': '#fbd75b',      // Banana (yellow)
        'AI': '#ffb878',                // Tangerine (orange)
        'DP': '#e1e1e1',                // Graphite (dark gray)
        'ČSAS Kalendář': '#5484ed',     // Blueberry (blue)
        'Sales': '#51b749',             // Basil (green)
        'Buřinka': '#dc2127'            // Tomato (red)
    },

    // Get color for a calendar label
    getLabelColor: function(label) {
        return this.labelColors[label] || '#9fc6e7'; // Default to light blue
    },

    // Get CSS class for a calendar label (CSP compliant)
    getLabelCssClass: function(label) {
        const labelMap = {
            'Finshape': 'label-finshape',
            'Osobní': 'label-osobni',
            'Grada': 'label-grada',
            'ČSAS Promise': 'label-csas-promise',
            'AI': 'label-ai',
            'DP': 'label-dp',
            'ČSAS Kalendář': 'label-csas-kalendar',
            'Sales': 'label-sales',
            'Buřinka': 'label-burinka'
        };
        return labelMap[label] || 'label-default';
    },

    // Get appropriate text color for a background color
    getTextColor: function(backgroundColor) {
        // Convert hex to RGB
        const hex = backgroundColor.replace('#', '');
        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);

        // Calculate luminance using the standard formula
        const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

        // Use a higher threshold (0.6) to ensure better contrast
        // This will make more colors use white text for better readability
        return luminance > 0.6 ? '#000000' : '#ffffff';
    },

    // Create calendar label badge HTML (CSP compliant)
    createLabelBadge: function(label) {
        if (!label) return '';
        return `<span class="badge ${this.getLabelCssClass(label)}">${label}</span>`;
    },

    // Initialize the application
    init: function() {
        this.bindEvents();
        this.checkApiStatus();
        this.initializeTooltips();
    },

    // Bind event listeners
    bindEvents: function() {
        // Week navigation
        document.addEventListener('click', (e) => {
            if (e.target.matches('.week-prev')) {
                this.navigateWeek(-1);
            } else if (e.target.matches('.week-next')) {
                this.navigateWeek(1);
            }
        });

        // Form submissions
        document.addEventListener('submit', (e) => {
            if (e.target.matches('#process-form')) {
                this.handleProcessForm(e);
            }
            // Note: #mapping-form is handled by mappings.html page-specific code
        });

        // Dynamic form updates
        document.addEventListener('change', (e) => {
            if (e.target.matches('#harvest-project-select')) {
                this.updateTaskOptions(e.target.value);
            }
        });
    },

    // Check API connection status
    checkApiStatus: function() {
        Promise.all([
            this.checkGoogleStatus(),
            this.checkHarvestStatus()
        ]).then(([googleStatus, harvestStatus]) => {
            this.updateStatusIndicators(googleStatus, harvestStatus);
        }).catch(error => {
            console.error('Error checking API status:', error);
        });
    },

    // Check Google Calendar connection
    checkGoogleStatus: function() {
        return fetch(`${this.config.apiBaseUrl}/google/status`)
            .then(response => response.json())
            .catch(() => ({ connected: false }));
    },

    // Check Harvest connection
    checkHarvestStatus: function() {
        return fetch(`${this.config.apiBaseUrl}/harvest/status`)
            .then(response => response.json())
            .catch(() => ({ connected: false }));
    },

    // Update status indicators in UI
    updateStatusIndicators: function(googleStatus, harvestStatus) {
        const googleIndicator = document.getElementById('google-status');
        const harvestIndicator = document.getElementById('harvest-status');

        if (googleIndicator) {
            this.updateStatusBadge(googleIndicator, googleStatus.connected, 'Google Calendar');
        }

        if (harvestIndicator) {
            this.updateStatusBadge(harvestIndicator, harvestStatus.connected, 'Harvest');
        }
    },

    // Update individual status badge
    updateStatusBadge: function(element, isConnected, serviceName) {
        const icon = isConnected ? 'bi-check-circle' : 'bi-circle';
        const badgeClass = isConnected ? 'bg-success' : 'bg-secondary';
        const statusText = isConnected ? 'Connected' : 'Not Connected';

        element.className = `badge status-badge ${badgeClass}`;
        element.innerHTML = `<i class="bi ${icon}"></i> ${serviceName}: ${statusText}`;
    },

    // Navigate week selection
    navigateWeek: function(direction) {
        const currentWeek = document.getElementById('current-week');
        if (!currentWeek) return;

        const currentDate = new Date(currentWeek.dataset.weekStart);
        currentDate.setDate(currentDate.getDate() + (direction * 7));

        this.updateWeekDisplay(currentDate);
        this.loadWeekEvents(currentDate);
    },

    // Update week display
    updateWeekDisplay: function(weekStart) {
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 6);

        const currentWeek = document.getElementById('current-week');
        if (currentWeek) {
            currentWeek.textContent = `${this.formatDate(weekStart)} - ${this.formatDate(weekEnd)}`;
            currentWeek.dataset.weekStart = this.formatDate(weekStart);
        }
    },

    // Load events for selected week
    loadWeekEvents: function(weekStart) {
        const weekStartStr = this.formatDate(weekStart);
        
        this.showLoading('Loading calendar events...');

        fetch(`${this.config.apiBaseUrl}/calendar/events?week_start=${weekStartStr}`)
            .then(response => response.json())
            .then(data => {
                this.displayWeekEvents(data.events);
                this.hideLoading();
            })
            .catch(error => {
                console.error('Error loading events:', error);
                this.showError('Failed to load calendar events');
                this.hideLoading();
            });
    },

    // Display calendar events
    displayWeekEvents: function(events) {
        const container = document.getElementById('events-container');
        if (!container) return;

        if (events.length === 0) {
            container.innerHTML = '<div class="alert alert-info">No calendar events found for this week.</div>';
            return;
        }

        const eventsHtml = events.map(event => this.renderEventPreview(event)).join('');
        container.innerHTML = eventsHtml;
    },

    // Render single event preview
    renderEventPreview: function(event) {
        const startTime = new Date(event.start).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const endTime = new Date(event.end).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const duration = this.calculateDuration(event.start, event.end);

        return `
            <div class="event-preview">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">${event.summary}</h6>
                        <div class="event-time">${startTime} - ${endTime}</div>
                        <div class="event-duration">${duration} hours</div>
                    </div>
                    <div class="text-end">
                        <span class="badge bg-info">${event.mapping || 'No mapping'}</span>
                    </div>
                </div>
            </div>
        `;
    },

    // Calculate duration between two times
    calculateDuration: function(start, end) {
        const startTime = new Date(start);
        const endTime = new Date(end);
        const diffMs = endTime - startTime;
        const diffHours = diffMs / (1000 * 60 * 60);
        return diffHours.toFixed(2);
    },



    // Update task options based on selected project
    updateTaskOptions: function(projectId) {
        if (!projectId) return;

        fetch(`${this.config.apiBaseUrl}/harvest/projects/${projectId}/tasks`)
            .then(response => response.json())
            .then(data => {
                const taskSelect = document.getElementById('harvest-task-select');
                if (taskSelect) {
                    taskSelect.innerHTML = '<option value="">Select a task...</option>';
                    data.tasks.forEach(task => {
                        taskSelect.innerHTML += `<option value="${task.id}">${task.name}</option>`;
                    });
                }
            })
            .catch(error => {
                console.error('Error loading tasks:', error);
            });
    },

    // Initialize Bootstrap tooltips
    initializeTooltips: function() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    // Utility functions
    formatDate: function(date) {
        // Use local date components to avoid timezone conversion issues
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    },

    showLoading: function(message = 'Loading...') {
        console.log('Loading:', message);

        // Remove existing loading overlay if any
        this.hideLoading();

        // Create loading overlay
        const loadingOverlay = document.createElement('div');
        loadingOverlay.id = 'loading-overlay';
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.innerHTML = `
            <div class="loading-content">
                <div class="spinner-border text-primary mb-3" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="loading-message">${message}</div>
            </div>
        `;

        // Add styles
        loadingOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            backdrop-filter: blur(2px);
        `;

        const loadingContent = loadingOverlay.querySelector('.loading-content');
        loadingContent.style.cssText = `
            background: white;
            padding: 2rem;
            border-radius: 0.5rem;
            text-align: center;
            box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
            min-width: 200px;
        `;

        const loadingMessage = loadingOverlay.querySelector('.loading-message');
        loadingMessage.style.cssText = `
            font-size: 1.1rem;
            color: #333;
            font-weight: 500;
        `;

        document.body.appendChild(loadingOverlay);
    },

    hideLoading: function() {
        console.log('Loading complete');
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.remove();
        }
    },

    showSuccess: function(message) {
        this.showAlert(message, 'success');
    },

    showError: function(message) {
        this.showAlert(message, 'danger');
    },

    showAlert: function(message, type) {
        // Create and show Bootstrap alert centered on screen
        const alertId = 'alert-' + Date.now();
        const alertHtml = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show js-alert" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        // Create or get the alerts container
        let alertsContainer = document.getElementById('js-alerts-container');
        if (!alertsContainer) {
            alertsContainer = document.createElement('div');
            alertsContainer.id = 'js-alerts-container';
            alertsContainer.className = 'js-alerts-container';
            document.body.appendChild(alertsContainer);
        }

        // Add the alert to the container
        alertsContainer.insertAdjacentHTML('beforeend', alertHtml);

        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                const bsAlert = new bootstrap.Alert(alertElement);
                bsAlert.close();
            }
        }, 5000);
    }
};

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    CalendarHarvestApp.init();
});
