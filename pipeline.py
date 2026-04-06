from fetcher import fetch_book_page, fetch_list_page
from parsers import extract_book_data, extract_book_urls
from db import save_book_to_db  # Now handles normalized schema internally
import requests  # Only for exception handling

# ============================================================================
# SCRAPING ORCHESTRATION - SINGLE BOOK
# ============================================================================


def scrape_single_book(book_url, db_name='goodreads_books.db'):
    """
    Scrape a single book and save it to the database.
    
    This is a convenience function that combines fetching, extracting, and saving.
    
    Args:
        book_url: Full URL to a Goodreads book page
        db_name: Name of the database file
        
    Returns:
        Dictionary containing the scraped book data, or None if scraping failed
    """
    try:
        print(f"\n→ Scraping: {book_url}")
        
        # Fetch the page HTML
        soup = fetch_book_page(book_url)
        
        # Extract the book data
        book_data = extract_book_data(soup)
        print(f"  Found: {book_data['title']} by {book_data['author']}")
        
        # Save to database
        save_book_to_db(book_data, book_url, db_name)
        
        return book_data
        
    except requests.exceptions.RequestException as e:
        # Handle network errors (connection issues, timeouts, etc.)
        print(f"✗ Network error scraping {book_url}: {e}")
        return None
        
    except Exception as e:
        # Catch any other unexpected errors
        print(f"✗ Error scraping {book_url}: {e}")
        return None


# ============================================================================
# SCRAPING ORCHESTRATION - LIST PAGE
# ============================================================================

def scrape_list_page(list_url, limit=20, db_name='goodreads_books.db'):
    """
    Scrape multiple books from a Goodreads list/genre page.
    
    This is the main function for list-page scraping. It:
    1. Fetches the list page
    2. Extracts book URLs from it
    3. Loops through each URL and scrapes the book
    4. Saves each book to the database
    
    Args:
        list_url: Full URL to a Goodreads list/genre page
        limit: Maximum number of books to scrape (default: 20)
        db_name: Name of the database file
        
    Returns:
        Number of books successfully scraped
    """
    print(f"\n{'='*80}")
    print(f"SCRAPING LIST PAGE")
    print(f"{'='*80}")
    print(f"URL: {list_url}")
    print(f"Limit: {limit} books")
    
    try:
        # Step 1: Fetch the list page
        print("\n[1/3] Fetching list page...")
        soup = fetch_list_page(list_url)
        print(f"✓ Page loaded: {soup.title.text if soup.title else 'Unknown'}")
        
        # Step 2: Extract book URLs
        print("\n[2/3] Extracting book URLs...")
        book_urls = extract_book_urls(soup, limit)
        
        if not book_urls:
            print("✗ No book URLs found on this page!")
            return 0
        
        # Step 3: Scrape each book
        print(f"\n[3/3] Scraping {len(book_urls)} books...")
        print(f"{'='*80}")
        
        success_count = 0
        
        # Loop through each book URL
        for i, book_url in enumerate(book_urls, start=1):
            print(f"\n[Book {i}/{len(book_urls)}]")
            
            # Scrape the book and save to database
            result = scrape_single_book(book_url, db_name)
            
            if result:
                success_count += 1
        
        # Summary
        print(f"\n{'='*80}")
        print(f"✓ COMPLETED: {success_count}/{len(book_urls)} books scraped successfully")
        print(f"{'='*80}")
        
        return success_count
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Network error fetching list page: {e}")
        return 0
        
    except Exception as e:
        print(f"✗ Error scraping list page: {e}")
        return 0


# ============================================================================
# ASYNC ORCHESTRATION
# ============================================================================
import asyncio
import aiohttp
from fetcher import fetch_page_async
from db import save_book_to_db_async  # Now handles normalized schema internally

async def scrape_single_book_async(session, book_url, db_name='goodreads_books.db'):
    """
    Async version of single book scraping.
    """
    try:
        print(f"debug: Starting {book_url}")
        soup = await fetch_page_async(book_url, session)
        print(f"debug: Fetched {book_url}")
        if not soup:
            return None
            
        book_data = extract_book_data(soup)
        
        await save_book_to_db_async(book_data, book_url, db_name)
        return book_data
        
    except Exception as e:
        print(f"✗ Error scraping {book_url}: {e}")
        return None

async def scrape_list_page_async(list_url, limit=20, db_name='goodreads_books.db'):
    """
    Scrape books concurrently using async/await.
    """
    print(f"\n{'='*80}")
    print(f"ASYNC SCRAPING LIST PAGE")
    print(f"{'='*80}")
    
    async with aiohttp.ClientSession() as session:
        print("\n[1/3] Fetching list page (Async)...")
        soup = await fetch_page_async(list_url, session)
        if not soup:
            print("Failed to fetch list page.")
            return 0
            
        print("\n[2/3] Extracting book URLs...")
        # reuse the synchronous parser (CPU bound operations are fine to keep sync for now)
        book_urls = extract_book_urls(soup, limit)
        
        if not book_urls:
            print("No books found.")
            return 0
            
        print(f"\n[3/3] Scraping {len(book_urls)} books CONCURRENTLY...")
        
        # Create tasks
        tasks = [scrape_single_book_async(session, url, db_name) for url in book_urls]
        
        # Run concurrently
        results = await asyncio.gather(*tasks)
        
        success_count = len([r for r in results if r is not None])
        
        print(f"\n{'='*80}")
        print(f"✓ COMPLETED (Async): {success_count}/{len(book_urls)} books scraped")
        print(f"{'='*80}")
        return success_count
