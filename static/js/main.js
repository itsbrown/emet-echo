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
    
    // Set active navigation link
    setActiveNavLink();
});

/**
 * Set up share buttons using Web Share API when available
 * or show custom social sharing dropdown menu
 */
function setupShareButtons() {
    const shareButtons = document.querySelectorAll('.share-button');
    
    // Create social sharing dropdown menu
    const createSocialShareMenu = (target, url, title) => {
        // Remove any existing menu
        const existingMenu = document.querySelector('.social-share-dropdown');
        if (existingMenu) {
            existingMenu.remove();
        }
        
        // Encode URL and title for sharing
        const encodedUrl = encodeURIComponent(url);
        const encodedTitle = encodeURIComponent(title);
        
        // Create the dropdown menu
        const menu = document.createElement('div');
        menu.className = 'social-share-dropdown dropdown-menu p-2';
        menu.innerHTML = `
            <h6 class="dropdown-header">Share via</h6>
            <a class="dropdown-item" href="https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}" target="_blank">
                <i class="bi bi-twitter me-2"></i>X (Twitter)
            </a>
            <a class="dropdown-item" href="https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}" target="_blank">
                <i class="bi bi-facebook me-2"></i>Facebook
            </a>
            <a class="dropdown-item" href="https://www.linkedin.com/shareArticle?mini=true&url=${encodedUrl}&title=${encodedTitle}" target="_blank">
                <i class="bi bi-linkedin me-2"></i>LinkedIn
            </a>
            <a class="dropdown-item" href="mailto:?subject=${encodedTitle}&body=${encodedTitle}%0A${encodedUrl}" target="_blank">
                <i class="bi bi-envelope me-2"></i>Email
            </a>
            <div class="dropdown-divider"></div>
            <a class="dropdown-item copy-link" href="#" data-url="${url}">
                <i class="bi bi-clipboard me-2"></i>Copy link
            </a>
        `;
        
        // Position the menu near the button
        const rect = target.getBoundingClientRect();
        menu.style.position = 'absolute';
        menu.style.top = rect.bottom + 'px';
        menu.style.left = rect.left + 'px';
        menu.style.zIndex = 1050;
        
        // Add to document
        document.body.appendChild(menu);
        
        // Add copy link handler
        const copyLinkButton = menu.querySelector('.copy-link');
        if (copyLinkButton) {
            copyLinkButton.addEventListener('click', (e) => {
                e.preventDefault();
                const linkUrl = copyLinkButton.getAttribute('data-url');
                copyToClipboard(linkUrl);
                
                // Show a toast notification
                const toastEl = document.getElementById('shareToast');
                if (toastEl) {
                    const toast = new bootstrap.Toast(toastEl);
                    toast.show();
                }
                
                // Close the menu
                menu.remove();
            });
        }
        
        // Close menu when clicking outside
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target) && e.target !== target) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    };
    
    // Add click handlers to all share buttons
    shareButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            
            const url = button.getAttribute('data-url');
            const title = button.getAttribute('data-title');
            
            // Check if Web Share API is available (mainly on mobile)
            if (navigator.share) {
                navigator.share({
                    title: title,
                    url: url
                })
                .then(() => console.log('Shared successfully'))
                .catch(error => {
                    console.error('Error sharing:', error);
                    // Fallback to custom menu if Web Share API fails
                    createSocialShareMenu(button, url, title);
                });
            } else {
                // Show custom share menu on desktop
                createSocialShareMenu(button, url, title);
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

/**
 * Set active navigation link based on current URL
 */
function setActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    // First, remove all active classes
    navLinks.forEach(link => {
        link.classList.remove('active');
    });
    
    // Set active class based on current path
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath) {
            link.classList.add('active');
        } else if (currentPath === '/' && href === '/') {
            link.classList.add('active');
        }
    });
}
