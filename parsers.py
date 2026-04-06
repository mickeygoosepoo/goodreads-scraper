# ============================================================================
# HTML PARSING FUNCTIONS
# ============================================================================
# 
# CS CONCEPT: Parsing & Data Extraction
# 
# A "parser" is a program that reads unstructured data (like raw HTML) and
# extracts structured data (like a Python dictionary) from it.
#
# This is a fundamental CS concept that appears everywhere:
#   - Compilers parse source code into an Abstract Syntax Tree (AST)
#   - JSON.parse() converts a string into a JavaScript object
#   - Our scraper parses HTML into a clean {title, author, rating, ...} dict
#
# The key idea: RAW DATA → PARSER → STRUCTURED DATA
# ============================================================================


def extract_book_data(soup):
    """
    Extract structured data from a book page's HTML.
    
    This function looks for specific HTML elements that contain the book's
    title, author, rating, genres, description, and page count.
    If an element isn't found, it provides a default value.
    
    DESIGN PATTERN: "Defensive Parsing"
    ------------------------------------
    Every extraction is wrapped in try/except. This is intentional.
    Real-world HTML is messy — Goodreads could change their CSS classes
    at any time, or a book page might be missing certain fields.
    
    Instead of crashing the entire scraper when one field is missing,
    we gracefully fall back to a default value. This is called
    "graceful degradation" — the system still works, just with less data.
    
    Args:
        soup: BeautifulSoup object of the book page
        
    Returns:
        Dictionary with keys: title, author, rating, genres, description, page_count
    """
    data = {}
    
    # ── Title ────────────────────────────────────────────────────────────
    # class_='Text__title1' is the CSS class Goodreads uses for book titles
    try:
        data['title'] = soup.find('h1', class_='Text__title1').text.strip()
    except AttributeError:
        # If the element isn't found, .find() returns None, and .text raises AttributeError
        data['title'] = 'Unknown'
    
    # ── Author ───────────────────────────────────────────────────────────
    try:
        data['author'] = soup.find('span', class_='ContributorLink__name').text.strip()
    except AttributeError:
        data['author'] = 'Unknown'
    
    # ── Rating ───────────────────────────────────────────────────────────
    try:
        data['rating'] = soup.find('div', class_='RatingStatistics__rating').text.strip()
    except AttributeError:
        data['rating'] = 'N/A'
    
    # ── Genres (NEW) ─────────────────────────────────────────────────────
    # 
    # CS CONCEPT: One-to-Many vs. Many-to-Many
    # 
    # A book has ONE author (one-to-many: one author → many books).
    # But a book can have MANY genres, and a genre can have MANY books.
    # This is a "many-to-many" relationship — a concept that's fundamental
    # to relational database design.
    #
    # Here we extract genres as a Python LIST. Later, in db.py, we'll see
    # how to store this many-to-many relationship using a "junction table."
    #
    # Goodreads stores genres as clickable buttons. We look for elements
    # with the class 'BookPageMetadataSection__genreButton' and extract
    # the text from each <a> tag's inner <span>.
    #
    try:
        genre_elements = soup.find_all('span', class_='BookPageMetadataSection__genreButton')
        # Extract the text from each genre element
        # List comprehension: a compact way to build a list by transforming each item
        #   [expression FOR item IN iterable]
        # is equivalent to:
        #   result = []
        #   for item in iterable:
        #       result.append(expression)
        data['genres'] = [g.find('span', class_='Button__labelItem').text.strip() 
                          for g in genre_elements 
                          if g.find('span', class_='Button__labelItem')]
    except (AttributeError, TypeError):
        data['genres'] = []
    
    # ── Description (NEW) ────────────────────────────────────────────────
    # 
    # The book description is stored in a <span> with class 'Formatted'.
    # We grab the text content and truncate it to avoid storing huge blobs.
    #
    # DESIGN DECISION: We store the first 1000 characters.
    # In a real production system you'd store the full text and truncate
    # in the UI layer. But for learning purposes, truncating at the DB
    # level keeps things simpler to inspect.
    #
    try:
        description_element = soup.find('span', class_='Formatted')
        if description_element:
            data['description'] = description_element.text.strip()[:1000]
        else:
            data['description'] = ''
    except AttributeError:
        data['description'] = ''
    
    # ── Page Count (NEW) ─────────────────────────────────────────────────
    #
    # The page count is displayed as text like "288 pages" within a
    # <p> tag that has the attribute data-testid="pagesFormat".
    #
    # We extract the number by splitting the string on spaces and taking
    # the first part: "288 pages" → "288" → 288
    #
    try:
        pages_element = soup.find('p', attrs={'data-testid': 'pagesFormat'})
        if pages_element:
            pages_text = pages_element.text.strip()
            # Split "288 pages" into ["288", "pages"] and take the first element
            # Then convert the string "288" to the integer 288
            data['page_count'] = int(pages_text.split()[0])
        else:
            data['page_count'] = None
    except (AttributeError, ValueError, IndexError):
        # ValueError: int() couldn't convert the string to a number
        # IndexError: the split() produced an empty list
        data['page_count'] = None
    
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
