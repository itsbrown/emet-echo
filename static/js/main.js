document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Share button functionality
    setupShareButtons();
    
    // Twitter share button with AI summary
    setupTwitterShareButtons();
    
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
        menu.className = 'social-share-dropdown dropdown-menu p-2 show';
        menu.innerHTML = `
            <h6 class="dropdown-header">Share via</h6>
            <a class="dropdown-item social-share-item" href="https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedTitle}" target="_blank">
                <i class="bi bi-twitter me-2"></i>X (Twitter)
            </a>
            <a class="dropdown-item social-share-item" href="https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}" target="_blank">
                <i class="bi bi-facebook me-2"></i>Facebook
            </a>
            <a class="dropdown-item social-share-item" href="https://www.linkedin.com/shareArticle?mini=true&url=${encodedUrl}&title=${encodedTitle}" target="_blank">
                <i class="bi bi-linkedin me-2"></i>LinkedIn
            </a>
            <a class="dropdown-item social-share-item" href="mailto:?subject=${encodedTitle}&body=${encodedTitle}%0A${encodedUrl}">
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
        button.addEventListener('click', event => {
            event.preventDefault();
            
            const url = button.getAttribute('data-url');
            const title = button.getAttribute('data-title');
            
            // Always use our custom sharing menu as the primary method
            // It's more reliable and works consistently across all browsers
            createSocialShareMenu(button, url, title);
            
            /* Disabled Web Share API due to frequent errors
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
            */
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
 * Set up Twitter share buttons with AI-generated summaries for executive orders
 */
function setupTwitterShareButtons() {
    const twitterShareButtons = document.querySelectorAll('.twitter-share-button');
    
    twitterShareButtons.forEach(button => {
        button.addEventListener('click', async function(event) {
            event.preventDefault();
            
            // Get the data attributes
            const orderText = this.getAttribute('data-order-text');
            const title = this.getAttribute('data-title');
            const url = this.getAttribute('data-url');
            
            // Show loading state
            const originalButtonText = this.innerHTML;
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
            this.disabled = true;
            
            try {
                // Get AI-generated Twitter summary via API call
                const response = await fetch('/api/generate-twitter-summary', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: orderText })
                });
                
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                
                const data = await response.json();
                let tweetText = data.summary;
                
                // Ensure tweet text isn't too long for Twitter (280 char limit minus url length)
                const maxLength = 230; // Leave room for URL
                if (tweetText.length > maxLength) {
                    tweetText = tweetText.substring(0, maxLength - 3) + '...';
                }
                
                // Encode for URL
                const encodedText = encodeURIComponent(tweetText);
                const encodedUrl = encodeURIComponent(url);
                
                // Open Twitter share window
                const twitterShareUrl = `https://twitter.com/intent/tweet?text=${encodedText}&url=${encodedUrl}`;
                window.open(twitterShareUrl, '_blank', 'width=550,height=420');
                
            } catch (error) {
                console.error('Error generating Twitter summary:', error);
                
                // Fallback: Share with just the title if AI summary generation fails
                const encodedTitle = encodeURIComponent(`Trump Executive Order: ${title}`);
                const encodedUrl = encodeURIComponent(url);
                const fallbackTwitterUrl = `https://twitter.com/intent/tweet?text=${encodedTitle}&url=${encodedUrl}`;
                window.open(fallbackTwitterUrl, '_blank', 'width=550,height=420');
                
            } finally {
                // Restore button state
                this.innerHTML = originalButtonText;
                this.disabled = false;
            }
        });
    });
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
