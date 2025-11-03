/**
 * CSRF Protection Utilities
 * Automatically adds CSRF tokens to all AJAX requests
 */

// Get CSRF token from meta tag
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : null;
}

// Setup CSRF token for all fetch requests
function setupCSRFProtection() {
    const originalFetch = window.fetch;
    
    window.fetch = function(url, options = {}) {
        console.log('🌐 FETCH INTERCEPTED:', url);

        // Only add CSRF token for same-origin requests
        if (!url.startsWith('http') || url.startsWith(window.location.origin)) {
            // Initialize headers if not present
            if (!options.headers) {
                options.headers = {};
            }

            // Add persistent token from localStorage for PyWebView compatibility
            const persistentToken = localStorage.getItem('persistent_token');
            console.log('   - Token from localStorage:', persistentToken ? persistentToken.substring(0, 20) + '...' : 'None');

            if (persistentToken) {
                if (options.headers instanceof Headers) {
                    options.headers.set('Authorization', `Bearer ${persistentToken}`);
                } else {
                    options.headers['Authorization'] = `Bearer ${persistentToken}`;
                }
                console.log('   - ✅ Authorization header added');
            } else {
                console.log('   - ⚠️  No token to add');
            }

            // Add CSRF token to POST, PUT, PATCH, DELETE requests
            if (options.method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method.toUpperCase())) {
                const token = getCSRFToken();
                if (token) {
                    // Add CSRF token header
                    if (options.headers instanceof Headers) {
                        options.headers.set('X-CSRFToken', token);
                    } else {
                        options.headers['X-CSRFToken'] = token;
                    }
                }
            }
        }

        return originalFetch.call(this, url, options);
    };
}

// Setup CSRF token for all XMLHttpRequest
function setupXHRCSRFProtection() {
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
        this._method = method;
        this._url = url;
        return originalOpen.call(this, method, url, async, user, password);
    };
    
    XMLHttpRequest.prototype.send = function(data) {
        // Add CSRF token for same-origin requests
        if ((!this._url.startsWith('http') || this._url.startsWith(window.location.origin)) &&
            this._method && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(this._method.toUpperCase())) {
            const token = getCSRFToken();
            if (token) {
                this.setRequestHeader('X-CSRFToken', token);
            }
        }
        
        return originalSend.call(this, data);
    };
}

// Add CSRF token to forms
function addCSRFToForms() {
    const forms = document.querySelectorAll('form');
    const token = getCSRFToken();
    
    if (!token) return;
    
    forms.forEach(form => {
        // Skip if form already has CSRF token
        if (form.querySelector('input[name="csrf_token"]')) return;
        
        // Only add to forms that POST to same origin
        const action = form.getAttribute('action') || window.location.pathname;
        const method = (form.getAttribute('method') || 'GET').toUpperCase();
        
        if (method === 'POST' && (!action.startsWith('http') || action.startsWith(window.location.origin))) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = token;
            form.appendChild(csrfInput);
        }
    });
}

// Initialize CSRF protection when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setupCSRFProtection();
    setupXHRCSRFProtection();
    addCSRFToForms();
    
    // Re-add CSRF tokens when new forms are added dynamically
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        if (node.tagName === 'FORM') {
                            addCSRFToForms();
                        } else if (node.querySelector && node.querySelector('form')) {
                            addCSRFToForms();
                        }
                    }
                });
            }
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Export for manual use
window.CSRFUtils = {
    getToken: getCSRFToken,
    addToForms: addCSRFToForms
};
