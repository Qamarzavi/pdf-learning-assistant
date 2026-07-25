// Common JavaScript functions for PDF Learning Assistant

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            setTimeout(function() {
                bsAlert.close();
            }, 5000);
        });
    }, 100);
});

// Form validation helper
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePassword(password) {
    return password.length >= 6;
}

// Loading button helper
function showLoading(button, text = 'Loading...') {
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner"></span> ' + text;
}

function hideLoading(button) {
    button.disabled = false;
    button.innerHTML = button.dataset.originalText;
}

// Copy to clipboard function
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        alert('Copied to clipboard!');
    }).catch(function(err) {
        console.error('Could not copy text: ', err);
    });
}

// Smooth scroll to element
function scrollToElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Confirm delete helper
function confirmDelete(message = 'Are you sure?') {
    return confirm(message);
}

// API call helper
async function apiCall(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        };
        
        if (data && (method === 'POST' || method === 'PUT')) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Something went wrong');
        }
        
        return result;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// CSRF Token helper (for AJAX requests)
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+U for upload
    if (e.ctrlKey && e.key === 'u') {
        e.preventDefault();
        const uploadLink = document.querySelector('a[href*="upload"]');
        if (uploadLink) window.location.href = uploadLink.href;
    }
    
    // Ctrl+H for home/dashboard
    if (e.ctrlKey && e.key === 'h') {
        e.preventDefault();
        const dashboardLink = document.querySelector('a[href*="dashboard"]');
        if (dashboardLink) window.location.href = dashboardLink.href;
    }
});