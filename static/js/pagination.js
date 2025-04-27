/**
 * Pagination functionality for loading more articles
 */
document.addEventListener('DOMContentLoaded', function() {
    // Find all load more buttons
    const loadMoreButtons = document.querySelectorAll('.load-more-btn');
    
    // Add click event listener to each button
    loadMoreButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const url = this.getAttribute('href');
            const category = new URL(url, window.location.origin).searchParams.get('category');
            const page = new URL(url, window.location.origin).searchParams.get('page');
            
            // Show loading indicator
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
            this.disabled = true;
            
            // Make AJAX request to get more articles
            fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                // Get the parent carousel container
                const carousel = this.closest('.article-carousel').querySelector('.row.flex-nowrap');
                
                // Remove the load more button
                this.parentElement.remove();
                
                // Add the new articles to the carousel
                data.articles.forEach(article => {
                    const articleHtml = createArticleCard(article);
                    
                    // Insert before the last child (which is the button we just removed)
                    carousel.insertAdjacentHTML('beforeend', articleHtml);
                });
                
                // If there are more articles available, add a new load more button
                if (data.more_available) {
                    const nextPage = parseInt(page) + 1;
                    const loadMoreHtml = `
                        <div class="col-auto d-flex align-items-center">
                            <a href="${window.location.pathname}?category=${category}&page=${nextPage}" 
                               class="btn btn-lg btn-outline-secondary load-more-btn">
                                <i class="bi bi-arrow-right-circle-fill"></i>
                                <span class="d-none d-md-inline ms-2">Load More</span>
                            </a>
                        </div>
                    `;
                    carousel.insertAdjacentHTML('beforeend', loadMoreHtml);
                    
                    // Reattach event listeners to the new button
                    const newButton = carousel.querySelector('.load-more-btn');
                    newButton.addEventListener('click', arguments.callee);
                }
                
                // Initialize the share buttons for the new articles
                setupShareButtons();
            })
            .catch(error => {
                console.error('Error loading more articles:', error);
                this.innerHTML = '<i class="bi bi-arrow-right-circle-fill"></i> Try Again';
                this.disabled = false;
            });
        });
    });
    
    /**
     * Create an article card HTML from article data
     */
    function createArticleCard(article) {
        // Format the date if available
        const publishedTime = article.published_time || '';
        
        // Get the source name if available
        const sourceName = article.source && article.source.name ? article.source.name : '';
        
        // Get the summary if available
        const summary = article.summary || 'No summary available.';
        
        return `
            <div class="col-md-4 col-lg-3">
                <div class="card news-card h-100 mx-2">
                    <!-- Article Image -->
                    <div class="article-img-container position-relative">
                        ${article.urlToImage 
                            ? `<img src="${article.urlToImage}" class="article-img" alt="${article.title}">`
                            : `<div class="img-placeholder"><i class="bi bi-image"></i></div>`
                        }
                        
                        <!-- Source Badge -->
                        ${sourceName 
                            ? `<span class="badge source-badge">${sourceName}</span>`
                            : ''
                        }
                    </div>
                    
                    <div class="card-body d-flex flex-column">
                        <!-- Published Date -->
                        ${publishedTime 
                            ? `<small class="text-muted mb-2">${publishedTime}</small>`
                            : ''
                        }
                        
                        <!-- Article Title -->
                        <h5 class="card-title truncate-2">${article.title}</h5>
                        
                        <!-- AI Summary -->
                        <p class="card-text truncate-3 flex-grow-1">${summary}</p>
                        
                        <!-- Action Buttons -->
                        <div class="d-flex justify-content-between align-items-center mt-3">
                            <a href="${article.url}" class="btn btn-sm btn-outline-primary" target="_blank">
                                Read Original
                                <i class="bi bi-box-arrow-up-right ms-1"></i>
                            </a>
                            
                            <button class="btn btn-sm btn-outline-secondary share-button" 
                                    data-url="${article.url}" 
                                    data-title="${article.title}"
                                    data-content="${article.description || article.summary}">
                                <i class="bi bi-share"></i>
                                Share
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
});