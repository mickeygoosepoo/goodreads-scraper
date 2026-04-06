from db import init_database, print_all_books, get_average_rating, get_genre_stats
from pipeline import scrape_single_book, scrape_list_page, scrape_list_page_async
import asyncio

# ============================================================================
# MAIN EXECUTION — Command-line scraper entry point
# ============================================================================
#
# This file is for running the scraper directly from the terminal.
# It is separate from app.py (the Flask web server).
#
# Usage:
#   ./venv/bin/python3 main.py
#
# Change the MODE variable below to switch between scraping modes.
# ============================================================================

if __name__ == "__main__":
    # Initialize the database (creates all 4 normalized tables if needed)
    init_database()
    
    # ========================================================================
    # CONFIGURATION — Change MODE to switch between scraping approaches
    # ========================================================================
    
    # Options: 'single', 'list', 'async_list'
    MODE = 'async_list'
    
    # ========================================================================
    # MODE 1: Scrape a single book by URL
    # ========================================================================
    
    if MODE == 'single':
        book_url = "https://www.goodreads.com/book/show/52578297-the-midnight-library"
        scrape_single_book(book_url)
    
    # ========================================================================
    # MODE 2: Scrape multiple books from a list page (sequential)
    # ========================================================================
    
    elif MODE == 'list':
        list_url = "https://www.goodreads.com/list/show/1.Best_Books_Ever"
        scrape_list_page(list_url, limit=10)

    # ========================================================================
    # MODE 3: Same as 'list' but fetch pages concurrently — much faster
    # ========================================================================
    
    elif MODE == 'async_list':
        list_url = "https://www.goodreads.com/list/show/1.Best_Books_Ever"
        asyncio.run(scrape_list_page_async(list_url, limit=10))
    
    else:
        print(f"✗ Invalid MODE: '{MODE}'")
        print("  Set MODE to 'single', 'list', or 'async_list'")
    
    # ========================================================================
    # DISPLAY RESULTS
    # ========================================================================
    
    print_all_books()

    average_rating = get_average_rating()
    print(f"\nAverage rating across all books: {average_rating:.2f}")

    genre_stats = get_genre_stats()
    if genre_stats:
        print("\nTop genres in your library:")
        for genre, count in genre_stats[:10]:
            print(f"  {genre}: {count} book{'s' if count != 1 else ''}")
