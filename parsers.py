# ============================================================================
# HTML PARSING FUNCTIONS
# ============================================================================

def extract_book_data(soup):
    """
    Extract structured data from a book page's HTML.
    
    This function looks for specific HTML elements that contain the book's
    title, author, and rating. If an element isn't found, it provides a default value.
    
    Args:
        soup: BeautifulSoup object of the book page
        
    Returns:
        Dictionary with keys: title, author, rating
    """
    data = {}
    
    # Try to find the book title
    # class_='Text__title1' is the CSS class Goodreads uses for book titles
    try:
        data['title'] = soup.find('h1', class_='Text__title1').text.strip()
    except AttributeError:
        # If the element isn't found, .find() returns None, and .text raises AttributeError
        data['title'] = 'Unknown'
    
    # Try to find the author name
    try:
        data['author'] = soup.find('span', class_='ContributorLink__name').text.strip()
    except AttributeError:
        data['author'] = 'Unknown'
    
    # Try to find the rating
    try:
        data['rating'] = soup.find('div', class_='RatingStatistics__rating').text.strip()
    except AttributeError:
        data['rating'] = 'N/A'
    
    return data


def extract_book_urls(soup, limit=20):
    """
    Extract book detail URLs from a list page.
    
    This function finds all links on the page that point to individual book pages,
    converts them to full URLs, removes duplicates, and limits the results.
    
    Args:
        soup: BeautifulSoup object of the list page
        limit: Maximum number of book URLs to return (default: 20)
        
    Returns:
        List of unique book URLs (strings)
    """
    book_urls = []
    
    # Find all <a> tags (links) on the page
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link['href']
        
        # Only keep links that contain '/book/show/'
        # This is the pattern Goodreads uses for book detail pages
        if '/book/show/' in href:
            
            # Convert relative URLs to absolute URLs
            # Relative: /book/show/123
            # Absolute: https://www.goodreads.com/book/show/123
            if href.startswith('/'):
                full_url = 'https://www.goodreads.com' + href
            elif href.startswith('http'):
                full_url = href
            else:
                # Skip malformed URLs
                continue
            
            # Remove query parameters and fragments for cleaner URLs
            # Example: https://www.goodreads.com/book/show/123?ref=nav -> https://www.goodreads.com/book/show/123
            if '?' in full_url:
                full_url = full_url.split('?')[0]
            if '#' in full_url:
                full_url = full_url.split('#')[0]
            
            # Add to our list
            book_urls.append(full_url)
    
    # Remove duplicates by converting to a set, then back to a list
    # Sets automatically remove duplicates because they only store unique values
    unique_urls = list(set(book_urls))
    
    # Limit the number of results
    # [:limit] is Python slice notation - it takes the first 'limit' items
    limited_urls = unique_urls[:limit]
    
    print(f"\n✓ Found {len(unique_urls)} unique book URLs (returning {len(limited_urls)})")
    
    return limited_urls
