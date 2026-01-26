# sqlite3 is Python's built-in module for working with SQLite databases
# No need to install it separately - it comes with Python!
import sqlite3
from datetime import datetime

# ============================================================================
# DATABASE FUNCTIONS
# ============================================================================

def init_database(db_name='goodreads_books.db'):
    """
    Initialize the SQLite database and create the books table if it doesn't exist.
    
    SQLite stores data in a single file on your computer (goodreads_books.db).
    This function sets up the structure (schema) for storing book data.
    
    Args:
        db_name: Name of the database file to create/use
        
    Returns:
        None
    """
    # Connect to the database (creates the file if it doesn't exist)
    # sqlite3.connect() returns a connection object that represents the database
    conn = sqlite3.connect(db_name)
    
    # A cursor is like a pointer that lets you execute SQL commands
    # Think of it as a tool to interact with the database
    cursor = conn.cursor()
    
    # Create the books table using SQL
    # IF NOT EXISTS prevents errors if the table already exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            -- AUTOINCREMENT means SQLite automatically assigns a unique ID
            
            title TEXT NOT NULL,
            -- TEXT is for strings, NOT NULL means this field is required
            
            author TEXT NOT NULL,
            rating TEXT,
            -- rating is optional (no NOT NULL), so it can be empty
            
            url TEXT UNIQUE,
            -- UNIQUE ensures we don't save the same book URL twice
            
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            -- Automatically records when the book was scraped
        )
    ''')
    
    # Commit saves the changes to the database
    # Without this, your changes would be lost!
    conn.commit()
    
    # Enable Write-Ahead Logging (WAL) for better concurrency
    # This allows the Web App to read while the Worker is writing
    try:
        cursor.execute('PRAGMA journal_mode=WAL;')
        # We need to fetch the result to complete the PRAGMA command
        journal_mode = cursor.fetchone()[0]
        print(f"✓ SQLite WAL mode enabled: {journal_mode}")
    except sqlite3.Error as e:
        print(f"✗ Failed to enable WAL mode: {e}")
    
    # Always close the connection when done to free up resources
    conn.close()
    
    print(f"✓ Database '{db_name}' initialized successfully!")


def save_book_to_db(book_data, book_url, db_name='goodreads_books.db'):
    """
    Save a single book's data to the SQLite database.
    
    This function takes the scraped book data and inserts it into the database.
    It handles duplicate URLs gracefully using INSERT OR REPLACE.
    
    Args:
        book_data: Dictionary containing book information (title, author, rating)
        book_url: The URL of the book page
        db_name: Name of the database file
        
    Returns:
        The ID of the inserted/updated book record
    """
    # Connect to the database
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    try:
        # INSERT OR REPLACE means: if the URL already exists, update it
        # Otherwise, create a new record
        # The ? placeholders prevent SQL injection attacks (security best practice)
        cursor.execute('''
            INSERT OR REPLACE INTO books (title, author, rating, url, scraped_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            book_data.get('title', 'Unknown'),  # .get() provides a default if key missing
            book_data.get('author', 'Unknown'),
            book_data.get('rating', 'N/A'),
            book_url,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Current timestamp
        ))
        
        # Commit the transaction to save changes
        conn.commit()
        
        # lastrowid gives us the ID of the row we just inserted
        book_id = cursor.lastrowid
        
        print(f"✓ Saved: {book_data.get('title', 'Unknown')} (ID: {book_id})")
        
        return book_id
        
    except sqlite3.Error as e:
        # If something goes wrong, print the error
        print(f"✗ Database error: {e}")
        return None
        
    finally:
        # Always close the connection, even if an error occurred
        conn.close()


def get_all_books(db_name='goodreads_books.db'):
    """
    Retrieve all books from the database.
    
    This is useful for viewing what you've scraped so far.
    
    Args:
        db_name: Name of the database file
        
    Returns:
        List of tuples, each containing book data
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # SELECT * means "get all columns"
    # FROM books means "from the books table"
    # ORDER BY sorts the results by scraped_at date (newest first)
    cursor.execute('SELECT * FROM books ORDER BY scraped_at DESC')
    
    # fetchall() retrieves all matching rows as a list of tuples
    books = cursor.fetchall()
    
    conn.close()
    
    return books


def print_all_books(db_name='goodreads_books.db'):
    """
    Print all books in the database in a readable format.
    
    This is a helper function to view your scraped data.
    """
    books = get_all_books(db_name)
    
    if not books:
        print("\nNo books in database yet.")
        return
    
    print(f"\n{'='*80}")
    print(f"BOOKS IN DATABASE ({len(books)} total)")
    print(f"{'='*80}\n")
    
    for book in books:
        # Each book is a tuple: (id, title, author, rating, url, scraped_at)
        book_id, title, author, rating, url, scraped_at = book
        print(f"ID: {book_id}")
        print(f"Title: {title}")
        print(f"Author: {author}")
        print(f"Rating: {rating}")
        print(f"URL: {url}")
        print(f"Scraped: {scraped_at}")
        print("-" * 80)

def get_average_rating(db_name='goodreads_books.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # AVG() is a built-in SQL function
    # CAST(rating AS FLOAT) converts the text "4.5" into the number 4.5
    cursor.execute('SELECT AVG(CAST(rating AS FLOAT)) FROM books WHERE rating != "N/A"')
    
    # fetchone() gets just the single result (the average)
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result[0] else 0

def delete_book(book_id, db_name='goodreads_books.db'):
    conn = sqlite3.connect(db_name) #
    cursor = conn.cursor() #
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit() #
    conn.close() #

# ============================================================================
# ASYNC DATABASE FUNCTIONS
# ============================================================================
import aiosqlite

async def save_book_to_db_async(book_data, book_url, db_name='goodreads_books.db'):
    """
    Asynchronously save a single book's data to the SQLite database.
    """
    try:
        async with aiosqlite.connect(db_name) as db:
            await db.execute('''
                INSERT OR REPLACE INTO books (title, author, rating, url, scraped_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                book_data.get('title', 'Unknown'),
                book_data.get('author', 'Unknown'),
                book_data.get('rating', 'N/A'),
                book_url,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            await db.commit()
            
            # grabbing the last row id is a bit detailed in valid SQL, 
            # but for this simple case we just want to know it worked.
            # aiosqlite cursor access is slightly different if we want lastrowid,
            # but usually we can just proceed.
            print(f"✓ Saved (Async): {book_data.get('title', 'Unknown')}")
            
    except Exception as e:
        print(f"✗ Database error: {e}")