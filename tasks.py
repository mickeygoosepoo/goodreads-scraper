import asyncio
import aiohttp
from celery.utils.log import get_task_logger
from celery_config import celery_app
from fetcher import fetch_page_async
from parsers import extract_book_urls, extract_book_data
from db import save_book_to_db_async

# Create a logger that shows up in the Celery worker terminal
logger = get_task_logger(__name__)

@celery_app.task(bind=True)
def scrape_list_task(self, list_url, limit=20):
    """
    Celery task to scrape a Goodreads list.
    
    This function:
    1. Sets up an asyncio event loop (since Celery is synchronous by default).
    2. Runs the async scraping logic inside that loop.
    """
    logger.info(f"Starting scrape task for: {list_url}")
    
    # We need to run the async code from within this sync task
    try:
        count = asyncio.run(scrape_list_async_logic(list_url, limit))
        logger.info(f"Task completed! Scraped {count} books.")
        return {"status": "completed", "books_scraped": count}
    except Exception as e:
        logger.error(f"Task failed: {e}")
        # self.retry(exc=e) # Optional: retry logic
        return {"status": "failed", "error": str(e)}

async def scrape_list_async_logic(list_url, limit):
    """
    The actual async logic, moved here from pipeline.py
    """
    async with aiohttp.ClientSession() as session:
        logger.info(f"[1/3] Fetching list page: {list_url}")
        
        # Use our existing async fetcher (now with SSL fix!)
        soup = await fetch_page_async(list_url, session)
        if not soup:
            logger.error("Failed to fetch list page.")
            return 0
            
        logger.info("[2/3] Extracting book URLs...")
        # Note: extract_book_urls is CPU-bound (sync), which is fine
        book_urls = extract_book_urls(soup, limit)
        
        if not book_urls:
            logger.warning("No books found.")
            return 0
            
        logger.info(f"[3/3] Scraping {len(book_urls)} books CONCURRENTLY...")
        
        # Create tasks for each book
        tasks = []
        for url in book_urls:
            # We call the helper function for single books
            tasks.append(scrape_single_book_helper(session, url))
            
        # Run them all at once
        results = await asyncio.gather(*tasks)
        
        # Count successes
        success_count = len([r for r in results if r is not None])
        return success_count

async def scrape_single_book_helper(session, book_url):
    """
    Helper for scraping one book.
    """
    try:
        logger.info(f"Scraping: {book_url}")
        soup = await fetch_page_async(book_url, session)
        if not soup:
            return None
            
        book_data = extract_book_data(soup)
        
        # Save to DB
        await save_book_to_db_async(book_data, book_url)
        logger.info(f"Saved: {book_data['title']}")
        return book_data
        
    except Exception as e:
        logger.error(f"Error scraping {book_url}: {e}")
        return None
