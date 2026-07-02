document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Share button functionality with AI summary
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
    
    // Async function to create social sharing menu, potentially with AI summary
    const createSocialShareMenu = async (target, url, title, content) => {
        // Show a temporary loading state on the button
        const originalButtonText = target.innerHTML;
        target.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
        target.disabled = true;
        
        // Remove any existing menu
        const existingMenu = document.querySelector('.social-share-dropdown');
        if (existingMenu) {
            existingMenu.remove();
        }
        
        let aiSummary = null;
        let shareTitle = title;
        let shareText = title;
        
        // Try to get AI summary if content is available
        if (content) {
            try {
                // Get AI-generated summary via API call
                const response = await fetch('/api/generate-twitter-summary', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: content, title: title })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    aiSummary = data.summary;
                    
                    // Use the AI summary as share text
                    if (aiSummary) {
                        // Limit length for sharing services
                        const maxLength = 230; // Leave room for URL
                        shareText = aiSummary.length > maxLength 
                            ? aiSummary.substring(0, maxLength - 3) + '...' 
                            : aiSummary;
                    }
                }
            } catch (error) {
                console.error('Error generating AI summary:', error);
                // Continue without AI summary if error occurs
            }
        }
        
        // Add "via EmetEcho.com" to the share text (avoid doubling if the AI summary already included it)
        if (!/via EmetEcho/i.test(shareText)) {
            shareText = shareText + " via EmetEcho.com";
        }
        
        // Encode URL and title for sharing
        const encodedUrl = encodeURIComponent(url);
        const encodedTitle = encodeURIComponent(title);
        const encodedShareText = encodeURIComponent(shareText);
        
        // Create the dropdown menu
        const menu = document.createElement('div');
        menu.className = 'social-share-dropdown dropdown-menu p-2 show';
        menu.innerHTML = `
            <h6 class="dropdown-header">Share via</h6>
            <a class="dropdown-item social-share-item" href="https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedShareText}" target="_blank">
                <i class="bi bi-twitter me-2"></i>X (Twitter)
            </a>
            <a class="dropdown-item social-share-item" href="https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}&quote=${encodedShareText}" target="_blank">
                <i class="bi bi-facebook me-2"></i>Facebook
            </a>
            <a class="dropdown-item social-share-item" href="https://www.linkedin.com/shareArticle?mini=true&url=${encodedUrl}&title=${encodedTitle}&summary=${encodedShareText}" target="_blank">
                <i class="bi bi-linkedin me-2"></i>LinkedIn
            </a>
            <a class="dropdown-item social-share-item" href="mailto:?subject=${encodedTitle}&body=${encodedShareText}%0A%0A${encodedUrl}">
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
        menu.style.top = (rect.bottom + window.scrollY) + 'px';
        
        // Ensure the menu doesn't go off-screen on mobile
        const viewportWidth = window.innerWidth;
        const menuWidth = 220; // Approximate width of the menu
        
        // If the menu would go off the right edge, align it to the right of the button
        if (rect.left + menuWidth > viewportWidth) {
            menu.style.right = (viewportWidth - rect.right - window.scrollX) + 'px';
        } else {
            menu.style.left = (rect.left + window.scrollX) + 'px';
        }
        
        menu.style.zIndex = 1050;
        
        // Restore button state
        target.innerHTML = originalButtonText;
        target.disabled = false;
        
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
        
        // Add click handlers to social links to close menu after click
        const socialLinks = menu.querySelectorAll('.social-share-item');
        socialLinks.forEach(link => {
            link.addEventListener('click', () => {
                // Close the menu after a small delay to ensure the link opens
                setTimeout(() => {
                    menu.remove();
                }, 100);
            });
        });
        
        // Close menu when clicking outside
        const closeMenuHandler = function(e) {
            if (!menu.contains(e.target) && e.target !== target) {
                menu.remove();
                document.removeEventListener('click', closeMenuHandler);
            }
        };
        
        // Use a setTimeout to avoid the immediate click triggering the close
        setTimeout(() => {
            document.addEventListener('click', closeMenuHandler);
        }, 0);
    };
    
    // Add click handlers to all share buttons
    shareButtons.forEach(button => {
        button.addEventListener('click', async (event) => {
            event.preventDefault();
            
            const url = button.getAttribute('data-url');
            const title = button.getAttribute('data-title');
            const content = button.getAttribute('data-content') || '';
            
            // Use our enhanced social sharing menu with AI summary
            await createSocialShareMenu(button, url, title, content);
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
