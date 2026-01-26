from db import init_database, print_all_books, get_average_rating
from pipeline import scrape_single_book, scrape_list_page, scrape_list_page_async
import asyncio

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Initialize the database (creates tables if they don't exist)
    init_database()
    
    # ========================================================================
    # CONFIGURATION - CHOOSE YOUR MODE
    # ========================================================================
    
    # Set this to 'single', 'list', or 'async_list'
    MODE = 'async_list'  # Try 'async_list' to see the speed difference!
    
    # ========================================================================
    # MODE 1: SCRAPE A SINGLE BOOK
    # ========================================================================
    
    if MODE == 'single':
        # Example: Scrape one specific book
        book_url = "https://www.goodreads.com/book/show/52578297-the-midnight-library"
        
        scrape_single_book(book_url)
    
    # ========================================================================
    # MODE 2: SCRAPE A LIST PAGE (SYNCHRONOUS)
    # ========================================================================
    
    elif MODE == 'list':
        # Example: Scrape books from a Goodreads list
        # You can use any Goodreads list, genre, or "best of" page URL
        list_url = "https://www.goodreads.com/list/show/1.Best_Books_Ever"
        
        # Limit controls how many books to scrape (default: 20)
        # Adjust this number based on your needs
        scrape_list_page(list_url, limit=10)

    # ========================================================================
    # MODE 3: SCRAPE A LIST PAGE (ASYNC / CONCURRENT)
    # ========================================================================
    
    elif MODE == 'async_list':
        list_url = "https://www.goodreads.com/list/show/1.Best_Books_Ever"
        
        # Notice how much faster this is than the synchronous 'list' mode!
        asyncio.run(scrape_list_page_async(list_url, limit=10))
    
    else:
        print(f"✗ Invalid MODE: {MODE}")
        print("Please set MODE to 'single', 'list', or 'async_list'")
    
    # ========================================================================
    # DISPLAY RESULTS
    # ========================================================================
    
    # Show all books currently in the database
    print_all_books()

    # Calculate and print the average rating
    average_rating = get_average_rating()
    print(f"Average rating: {average_rating:.2f}")
