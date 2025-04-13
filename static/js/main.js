document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Share button functionality
    setupShareButtons();
    
    // Initialize loading state for articles
    setupLazyLoading();
    
    // Setup search functionality
    setupSearch();
});

/**
 * Set up share buttons using Web Share API when available
 */
function setupShareButtons() {
    const shareButtons = document.querySelectorAll('.share-button');
    
    shareButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            
            const url = button.getAttribute('data-url');
            const title = button.getAttribute('data-title');
            
            // Check if Web Share API is available
            if (navigator.share) {
                navigator.share({
                    title: title,
                    url: url
                })
                .then(() => console.log('Shared successfully'))
                .catch(error => console.error('Error sharing:', error));
            } else {
                // Fallback - copy to clipboard
                copyToClipboard(url);
                
                // Show a toast notification
                const toastEl = document.getElementById('shareToast');
                if (toastEl) {
                    const toast = new bootstrap.Toast(toastEl);
                    toast.show();
                }
            }
        });
    });
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    // Create a temporary input element
    const input = document.createElement('input');
    input.style.position = 'fixed';
    input.style.opacity = 0;
    input.value = text;
    document.body.appendChild(input);
    
    // Select and copy the text
    input.select();
    document.execCommand('copy');
    
    // Remove the temporary element
    document.body.removeChild(input);
}

/**
 * Set up lazy loading for article images
 */
function setupLazyLoading() {
    const articleImages = document.querySelectorAll('.article-img');
    
    articleImages.forEach(img => {
        // Set a placeholder if image fails to load
        img.addEventListener('error', function() {
            // Replace with placeholder
            const container = this.parentElement;
            if (container) {
                const placeholder = document.createElement('div');
                placeholder.className = 'img-placeholder';
                placeholder.innerHTML = '<i class="bi bi-image"></i><span class="ms-2">Image not available</span>';
                container.replaceChild(placeholder, this);
            }
        });
    });
}

/**
 * Set up search functionality
 */
function setupSearch() {
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchInput');
    
    if (searchForm && searchInput) {
        searchForm.addEventListener('submit', function(event) {
            // Don't submit if search is empty
            if (!searchInput.value.trim()) {
                event.preventDefault();
                searchInput.focus();
            }
        });
    }
}

/**
 * Refresh news content
 */
function refreshNews() {
    const refreshButton = document.getElementById('refreshButton');
    
    if (refreshButton) {
        // Disable button and show spinner
        refreshButton.disabled = true;
        refreshButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Refreshing...';
        
        // Redirect to refresh endpoint
        window.location.href = '/refresh';
    }
}
