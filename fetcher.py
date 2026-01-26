import requests
from bs4 import BeautifulSoup

# ============================================================================
# HTTP FETCHING FUNCTIONS
# ============================================================================

def fetch_book_page(book_url):
    """
    Fetch a Goodreads book page and return parsed HTML.
    
    This function handles the HTTP request and returns a BeautifulSoup object
    that we can use to extract data from the page.
    
    Args:
        book_url: Full URL to a Goodreads book page
        
    Returns:
        BeautifulSoup object containing the parsed HTML
    """
    # Set a User-Agent header to mimic a real browser
    # Some websites block requests without this
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(book_url, headers=headers)
    response.raise_for_status()  # Raises error for bad status codes (404, 500, etc.)
    
    # Parse the HTML using lxml parser (faster than html.parser)
    return BeautifulSoup(response.text, 'lxml')


def fetch_list_page(list_url):
    """
    Fetch a Goodreads list/genre page and return parsed HTML.
    
    This works the same as fetch_book_page, but we give it a different name
    for clarity - it's fetching a list page, not a book page.
    
    Args:
        list_url: Full URL to a Goodreads list/genre page
        
    Returns:
        BeautifulSoup object containing the parsed HTML
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(list_url, headers=headers)
    response.raise_for_status()
    
    return BeautifulSoup(response.text, 'lxml')


# ============================================================================
# ASYNC FETCHING FUNCTIONS
# ============================================================================
import aiohttp
import asyncio

async def fetch_page_async(url, session):
    """
    Asynchronously fetch a page and return parsed HTML.
    
    Args:
        url: URL to fetch
        session: aiohttp.ClientSession object
        
    Returns:
        BeautifulSoup object or None if failed
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        async with session.get(url, headers=headers, ssl=False) as response:
            response.raise_for_status()
            html = await response.text()
            return BeautifulSoup(html, 'lxml')
    except Exception as e:
        print(f"✗ Error fetching {url}: {e}")
        return None
