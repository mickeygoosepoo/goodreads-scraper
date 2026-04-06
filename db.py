# ============================================================================
# DATABASE LAYER — NORMALIZED RELATIONAL SCHEMA
# ============================================================================
#
# CS CONCEPT: Database Normalization (1NF → 2NF → 3NF)
#
# "Normalization" is the process of organizing a database to reduce
# redundancy (duplicate data) and improve data integrity (correctness).
#
# ┌─────────────────────────────────────────────────────────────────────┐
# │  BEFORE (Denormalized / "Flat Table"):                             │
# │                                                                     │
# │  books: id | title | author | rating | url | scraped_at            │
# │                                                                     │
# │  Problem: If "Matt Haig" writes 5 books, his name is stored        │
# │  5 times. If we want to fix a typo in his name, we must update     │
# │  ALL 5 rows. This is called an "Update Anomaly."                   │
# │                                                                     │
# │  AFTER (Normalized):                                                │
# │                                                                     │
# │  authors: id | name                                                │
# │  books:   id | title | author_id (FK) | rating | ...               │
# │  genres:  id | name                                                │
# │  book_genres: book_id (FK) | genre_id (FK)                        │
# │                                                                     │
# │  Now "Matt Haig" is stored ONCE in the authors table.              │
# │  Books reference him by his ID (a Foreign Key).                    │
# │  Fix the typo once → it's fixed everywhere.                        │
# └─────────────────────────────────────────────────────────────────────┘
#
# THE THREE NORMAL FORMS (simplified):
#
#   1NF: Every cell contains a single value (no lists in a column).
#        Our old table violated this if we tried to store genres as
#        "Fiction, Fantasy, Adventure" in one column.
#
#   2NF: Every non-key column depends on the ENTIRE primary key.
#        Basically: don't mix unrelated data in the same table.
#
#   3NF: No column depends on another non-key column.
#        Example: If we stored author_name AND author_country in the
#        books table, author_country depends on author_name, not on
#        the book. That belongs in a separate authors table.
#
# ============================================================================

import sqlite3
from datetime import datetime

# ============================================================================
# DATABASE PATH — Single source of truth
# ============================================================================
# 
# DESIGN PRINCIPLE: "Don't Repeat Yourself" (DRY)
# Instead of passing 'goodreads_books.db' to every function, we define it
# once here. If we ever rename the database, we change ONE line.
#
DB_NAME = 'goodreads_books.db'


# ============================================================================
# SCHEMA INITIALIZATION
# ============================================================================

def init_database(db_name=DB_NAME):
    """
    Initialize the SQLite database with a NORMALIZED schema.
    
    Creates 4 tables:
      1. authors     — One row per unique author
      2. books       — One row per book, references an author via foreign key
      3. genres      — One row per unique genre
      4. book_genres — Junction table linking books to genres (many-to-many)
    
    CS CONCEPT: Foreign Keys & Referential Integrity
    -------------------------------------------------
    A Foreign Key (FK) is a column that references the Primary Key (PK) of
    another table. It creates a "link" between the two tables.
    
    Example: books.author_id → authors.id
    
    "Referential Integrity" means the database GUARANTEES that every
    author_id in the books table corresponds to a real row in the authors
    table. You can't insert a book with author_id=999 if there's no
    author with id=999. The database will reject the insert.
    
    This prevents "orphan records" — data that references something
    that doesn't exist.
    
    Args:
        db_name: Name of the database file to create/use
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # ── IMPORTANT: Enable Foreign Key enforcement ────────────────────────
    # SQLite has foreign keys but they're DISABLED by default (!).
    # We must explicitly enable them with this PRAGMA.
    # Without this line, foreign key constraints are silently ignored.
    cursor.execute('PRAGMA foreign_keys = ON;')
    
    # ── Table 1: AUTHORS ─────────────────────────────────────────────────
    # 
    # This table stores each unique author ONCE.
    # The UNIQUE constraint on 'name' prevents duplicate author entries.
    #
    # CS CONCEPT: Entity Table
    # An "entity table" represents a real-world thing (person, place, item).
    # Each row is one instance of that entity.
    #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
            -- UNIQUE: "Matt Haig" can only appear once in this table.
            -- If we try to INSERT a duplicate, SQLite will reject it
            -- (or we can use INSERT OR IGNORE to silently skip it).
        )
    ''')
    
    # ── Table 2: BOOKS ───────────────────────────────────────────────────
    #
    # This table stores book data. Instead of storing the author's NAME
    # directly, it stores an author_id that REFERENCES the authors table.
    #
    # CS CONCEPT: Foreign Key (FK)
    # The line `FOREIGN KEY (author_id) REFERENCES authors(id)` means:
    #   "The value in author_id MUST be a valid id from the authors table."
    #
    # This is the fundamental mechanism for linking tables together.
    #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            
            author_id INTEGER NOT NULL,
            -- Instead of storing "Matt Haig" here, we store the NUMBER
            -- that represents Matt Haig in the authors table (e.g., 7).
            -- This is the core idea of normalization.
            
            rating TEXT,
            description TEXT DEFAULT '',
            page_count INTEGER,
            url TEXT UNIQUE,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (author_id) REFERENCES authors(id)
            -- This constraint tells SQLite: "author_id must be a valid
            -- id from the authors table. Don't let me insert garbage."
        )
    ''')
    
    # ── Table 3: GENRES ──────────────────────────────────────────────────
    #
    # Like authors, each genre is stored ONCE.
    # "Fiction" appears in this table exactly once, with its own id.
    #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # ── Table 4: BOOK_GENRES (Junction Table) ────────────────────────────
    #
    # CS CONCEPT: Junction Table (aka Bridge Table, Associative Table)
    #
    # This is the most important new concept in this refactor.
    #
    # THE PROBLEM:
    #   A book can have MANY genres.  (Harry Potter → Fantasy, Adventure, YA)
    #   A genre can have MANY books.  (Fantasy → Harry Potter, LOTR, Narnia)
    #   This is a "Many-to-Many" relationship.
    #
    # THE RULE:
    #   You CANNOT represent a many-to-many relationship with just two tables.
    #   You need a THIRD table in the middle — the "junction table."
    #
    # HOW IT WORKS:
    #   book_genres has two foreign keys: one pointing to books, one to genres.
    #   Each ROW represents one link: "Book X belongs to Genre Y."
    #
    #   Example data:
    #     book_id | genre_id
    #     --------|--------
    #        1    |    3      ← "Harry Potter" is in "Fantasy"
    #        1    |    7      ← "Harry Potter" is also in "Adventure"
    #        2    |    3      ← "LOTR" is also in "Fantasy"
    #
    #   To find all genres for Harry Potter: WHERE book_id = 1
    #   To find all Fantasy books: WHERE genre_id = 3
    #
    #   PRIMARY KEY (book_id, genre_id) is a "Composite Primary Key" —
    #   the combination of both columns must be unique. This prevents
    #   linking the same book to the same genre twice.
    #
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_genres (
            book_id INTEGER NOT NULL,
            genre_id INTEGER NOT NULL,
            
            PRIMARY KEY (book_id, genre_id),
            -- Composite PK: the PAIR (book_id, genre_id) must be unique.
            -- Book 1 can be in Genre 3, and Book 1 can be in Genre 7,
            -- but Book 1 cannot be in Genre 3 twice.
            
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
            -- ON DELETE CASCADE: If a book is deleted from the books table,
            -- automatically delete all its entries in book_genres too.
            -- Without this, deleting a book would leave "orphan" rows here.
            
            FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    
    # ── Enable WAL mode for concurrent access ────────────────────────────
    # WAL = Write-Ahead Logging. Allows the Flask app to read while
    # the Celery worker is writing. Without this, reads would block writes.
    try:
        cursor.execute('PRAGMA journal_mode=WAL;')
        journal_mode = cursor.fetchone()[0]
        print(f"✓ SQLite WAL mode enabled: {journal_mode}")
    except sqlite3.Error as e:
        print(f"✗ Failed to enable WAL mode: {e}")
    
    conn.close()
    print(f"✓ Database '{db_name}' initialized with normalized schema!")
    print(f"  Tables: authors, books, genres, book_genres")


# ============================================================================
# HELPER: Get or Create (Upsert Pattern)
# ============================================================================
#
# CS CONCEPT: Idempotency
#
# An operation is "idempotent" if doing it multiple times has the same
# effect as doing it once. Inserting "Matt Haig" into authors should
# work the first time AND the hundredth time without error or duplicates.
#
# The pattern below achieves this:
#   1. Try to INSERT. If the name already exists, IGNORE the insert.
#   2. SELECT the row to get its id (works whether we just inserted or not).
#
# This is sometimes called "Upsert" (UPDATE + INSERT) or "Get or Create."
# Django has get_or_create(), Rails has find_or_create_by().
# ============================================================================

def _get_or_create_author(cursor, author_name):
    """
    Get the author's ID, creating the author record if it doesn't exist.
    
    This is a private helper function (prefixed with _ by convention).
    It's only meant to be called by other functions in this module,
    not by external code.
    
    Args:
        cursor: SQLite cursor (we pass the cursor instead of creating a
                new connection so this runs inside the caller's transaction)
        author_name: The author's name string
        
    Returns:
        The author's id (integer)
    """
    # INSERT OR IGNORE: If the name already exists, do nothing (no error)
    cursor.execute(
        'INSERT OR IGNORE INTO authors (name) VALUES (?)',
        (author_name,)
    )
    
    # Now SELECT to get the id. This works whether we just inserted
    # a new row OR the author already existed.
    cursor.execute('SELECT id FROM authors WHERE name = ?', (author_name,))
    return cursor.fetchone()[0]


def _get_or_create_genre(cursor, genre_name):
    """
    Get the genre's ID, creating the genre record if it doesn't exist.
    Same pattern as _get_or_create_author.
    """
    cursor.execute(
        'INSERT OR IGNORE INTO genres (name) VALUES (?)',
        (genre_name,)
    )
    cursor.execute('SELECT id FROM genres WHERE name = ?', (genre_name,))
    return cursor.fetchone()[0]


# ============================================================================
# SAVE BOOK (with full relational linking)
# ============================================================================

def save_book_to_db(book_data, book_url, db_name=DB_NAME):
    """
    Save a book and all its related data to the normalized database.
    
    This is a MULTI-STEP operation:
      1. Get or create the author → get author_id
      2. Insert the book with author_id as a foreign key
      3. Get or create each genre → get genre_ids
      4. Link book to genres in the junction table
    
    CS CONCEPT: Database Transactions (ACID)
    -----------------------------------------
    All 4 steps above happen inside a single TRANSACTION.
    
    A transaction is like an "all or nothing" guarantee:
    - If ALL steps succeed → COMMIT (save everything)
    - If ANY step fails → ROLLBACK (undo everything)
    
    This prevents "partial saves" where, for example, the book is saved
    but the genre links fail, leaving the database in an inconsistent state.
    
    The properties of a good transaction are called ACID:
      A - Atomicity:    All steps succeed or all steps fail
      C - Consistency:  The database stays in a valid state
      I - Isolation:    Concurrent transactions don't interfere
      D - Durability:   Once committed, the data survives crashes
    
    Args:
        book_data: Dictionary with keys: title, author, rating, genres,
                   description, page_count
        book_url:  The URL of the book page (used as unique identifier)
        db_name:   Name of the database file
        
    Returns:
        The ID of the inserted/updated book record, or None on error
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Enable foreign key enforcement for this connection
    cursor.execute('PRAGMA foreign_keys = ON;')
    
    try:
        # ── Step 1: Get or create the author ─────────────────────────────
        author_name = book_data.get('author', 'Unknown')
        author_id = _get_or_create_author(cursor, author_name)
        
        # ── Step 2: Insert/update the book ───────────────────────────────
        #
        # We use INSERT OR REPLACE keyed on the URL.
        # If a book with this URL already exists, it gets updated.
        # If it's new, it gets inserted.
        #
        cursor.execute('''
            INSERT OR REPLACE INTO books 
                (title, author_id, rating, description, page_count, url, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            book_data.get('title', 'Unknown'),
            author_id,
            book_data.get('rating', 'N/A'),
            book_data.get('description', ''),
            book_data.get('page_count'),
            book_url,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        # Get the book's ID (either the new one or the replaced one)
        book_id = cursor.lastrowid
        
        # ── Step 3 & 4: Link genres ─────────────────────────────────────
        #
        # First, clear any existing genre links for this book.
        # This handles the case where we're RE-scraping a book that
        # already exists — we want fresh genre data, not duplicates.
        #
        cursor.execute('DELETE FROM book_genres WHERE book_id = ?', (book_id,))
        
        # Now create fresh links for each genre
        genres = book_data.get('genres', [])
        for genre_name in genres:
            genre_id = _get_or_create_genre(cursor, genre_name)
            
            # Insert the link into the junction table
            # INSERT OR IGNORE prevents errors if the same genre appears twice
            # in the scraped data (defensive programming)
            cursor.execute(
                'INSERT OR IGNORE INTO book_genres (book_id, genre_id) VALUES (?, ?)',
                (book_id, genre_id)
            )
        
        # ── COMMIT the transaction ───────────────────────────────────────
        # Everything above succeeds? Great, save it all atomically.
        conn.commit()
        
        genre_str = ', '.join(genres[:3]) if genres else 'no genres'
        print(f"✓ Saved: {book_data.get('title', 'Unknown')} by {author_name} [{genre_str}] (ID: {book_id})")
        
        return book_id
        
    except sqlite3.Error as e:
        # ── ROLLBACK on error ────────────────────────────────────────────
        # Something went wrong. Undo ALL changes from this transaction
        # to prevent a "half-saved" book with missing genre links.
        conn.rollback()
        print(f"✗ Database error: {e}")
        return None
        
    finally:
        conn.close()


# ============================================================================
# QUERY FUNCTIONS — Using SQL JOINs
# ============================================================================
#
# CS CONCEPT: SQL JOINs
#
# Since our data is now split across multiple tables, we need a way to
# "reassemble" it. SQL JOINs combine rows from two or more tables based
# on a related column (usually a foreign key).
#
# Types of JOINs:
#
#   INNER JOIN: Only rows that have matches in BOTH tables
#     books INNER JOIN authors → only books that HAVE an author
#
#   LEFT JOIN:  ALL rows from the left table, even if no match on the right
#     books LEFT JOIN authors → all books, even if author_id is somehow NULL
#
#   We use LEFT JOIN here because it's safer — we always get all books
#   even if some data is missing. INNER JOIN would silently drop books
#   with missing author records.
#
# ============================================================================

def get_all_books(db_name=DB_NAME):
    """
    Retrieve all books with their author names and genre lists.
    
    This uses a LEFT JOIN to combine data from the books and authors tables.
    
    CS CONCEPT: The N+1 Query Problem (and how we avoid it)
    --------------------------------------------------------
    A naive approach would be:
      1. SELECT * FROM books               → get 55 books
      2. For each book: SELECT * FROM authors WHERE id = author_id
         → That's 55 MORE queries!
    
    This is called the "N+1 problem" (1 query + N follow-up queries).
    It's a classic performance anti-pattern.
    
    Instead, we use a JOIN to get everything in ONE query.
    The database does the combining internally, which is vastly faster.
    
    Returns:
        List of tuples: (id, title, author_name, rating, url, scraped_at,
                         description, page_count, genres_string)
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # ── The JOIN query ───────────────────────────────────────────────────
    #
    # Let's break this query down:
    #
    #   SELECT b.id, b.title, a.name, ...
    #     → We're selecting columns from TWO tables (b = books, a = authors)
    #     → "a.name AS author_name" gives the column a friendly alias
    #
    #   FROM books b
    #     → Start with the books table, give it alias "b"
    #
    #   LEFT JOIN authors a ON b.author_id = a.id
    #     → For each book, find the author whose id matches book.author_id
    #     → LEFT JOIN means: keep the book even if no matching author exists
    #
    #   ORDER BY b.scraped_at DESC
    #     → Newest books first
    #
    cursor.execute('''
        SELECT 
            b.id,
            b.title,
            a.name AS author_name,
            b.rating,
            b.url,
            b.scraped_at,
            b.description,
            b.page_count
        FROM books b
        LEFT JOIN authors a ON b.author_id = a.id
        ORDER BY b.scraped_at DESC
    ''')
    
    books = cursor.fetchall()
    
    # ── Fetch genres for each book ───────────────────────────────────────
    #
    # For the genre list, we need to query the junction table.
    # We do a second query per book here. Yes, this is technically N+1!
    #
    # In a production system, you'd solve this with a more complex query
    # using GROUP_CONCAT or by fetching all genres in one query and mapping
    # them in Python. But for learning, this explicit approach is clearer.
    #
    result = []
    for book in books:
        book_id = book[0]
        
        # Query the junction table, joining with genres to get the names
        cursor.execute('''
            SELECT g.name
            FROM book_genres bg
            JOIN genres g ON bg.genre_id = g.id
            WHERE bg.book_id = ?
        ''', (book_id,))
        
        genres = [row[0] for row in cursor.fetchall()]
        genre_string = ', '.join(genres) if genres else ''
        
        # Append the genre string to the book tuple
        # book + (genre_string,) creates a new tuple with the extra field
        result.append(book + (genre_string,))
    
    conn.close()
    return result


def get_books_by_author(author_name, db_name=DB_NAME):
    """
    Get all books by a specific author.
    
    This demonstrates filtering with a JOIN — we join books to authors
    and then filter by author name.
    
    CS CONCEPT: Query Optimization
    ───────────────────────────────
    Because author names are in a separate table with a UNIQUE constraint,
    SQLite can use an index to find the author quickly (O(log n) instead
    of O(n) — scanning every row). This is one of the benefits of
    normalization: the database can optimize lookups on smaller tables.
    
    Args:
        author_name: The author's name to filter by
        
    Returns:
        List of tuples with book data
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Notice: we filter on a.name (the authors table), but we're selecting
    # from books. The JOIN makes this possible.
    cursor.execute('''
        SELECT 
            b.id, b.title, a.name, b.rating, b.url, b.scraped_at,
            b.description, b.page_count
        FROM books b
        JOIN authors a ON b.author_id = a.id
        WHERE a.name = ?
        ORDER BY b.scraped_at DESC
    ''', (author_name,))
    
    books = cursor.fetchall()
    
    # Fetch genres for each book (same pattern as get_all_books)
    result = []
    for book in books:
        book_id = book[0]
        cursor.execute('''
            SELECT g.name FROM book_genres bg
            JOIN genres g ON bg.genre_id = g.id
            WHERE bg.book_id = ?
        ''', (book_id,))
        genres = [row[0] for row in cursor.fetchall()]
        result.append(book + (', '.join(genres),))
    
    conn.close()
    return result


def get_books_by_genre(genre_name, db_name=DB_NAME):
    """
    Get all books in a specific genre.
    
    This is the most complex query so far — it chains TWO JOINs:
      books → book_genres (junction) → genres
    
    CS CONCEPT: Multi-table JOINs
    ──────────────────────────────
    You can chain as many JOINs as you need. Each JOIN adds another
    table to the "virtual combined table" that SQL is building.
    
    The execution order (simplified):
      1. Start with books
      2. JOIN book_genres to find genre links for each book
      3. JOIN genres to get the genre names
      4. WHERE filters to only the genre we want
    
    Args:
        genre_name: The genre name to filter by
        
    Returns:
        List of tuples with book data
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # ── Chained JOIN ─────────────────────────────────────────────────────
    # 
    # books → book_genres → genres
    #
    # We start at books, join to book_genres using book_id,
    # then join to genres using genre_id, then filter by genre name.
    #
    cursor.execute('''
        SELECT 
            b.id, b.title, a.name, b.rating, b.url, b.scraped_at,
            b.description, b.page_count
        FROM books b
        JOIN authors a ON b.author_id = a.id
        JOIN book_genres bg ON b.id = bg.book_id
        JOIN genres g ON bg.genre_id = g.id
        WHERE g.name = ?
        ORDER BY b.scraped_at DESC
    ''', (genre_name,))
    
    books = cursor.fetchall()
    
    # Fetch all genres for each book (not just the one we filtered by)
    result = []
    for book in books:
        book_id = book[0]
        cursor.execute('''
            SELECT g.name FROM book_genres bg
            JOIN genres g ON bg.genre_id = g.id
            WHERE bg.book_id = ?
        ''', (book_id,))
        genres = [row[0] for row in cursor.fetchall()]
        result.append(book + (', '.join(genres),))
    
    conn.close()
    return result


def get_genre_stats(db_name=DB_NAME):
    """
    Get a count of books per genre.
    
    CS CONCEPT: Aggregation with GROUP BY
    ──────────────────────────────────────
    GROUP BY collapses multiple rows into one per group.
    COUNT(*) then counts how many rows are in each group.
    
    Example:
      Genre    | book_id     →  GROUP BY genre  →  Genre    | COUNT(*)
      Fantasy  | 1                                  Fantasy  | 3
      Fantasy  | 2                                  Sci-Fi   | 2
      Fantasy  | 5
      Sci-Fi   | 3
      Sci-Fi   | 4
    
    Returns:
        List of tuples: (genre_name, book_count), ordered by count descending
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT g.name, COUNT(*) as book_count
        FROM genres g
        JOIN book_genres bg ON g.id = bg.genre_id
        GROUP BY g.name
        ORDER BY book_count DESC
    ''')
    
    stats = cursor.fetchall()
    conn.close()
    return stats


def get_average_rating(db_name=DB_NAME):
    """
    Calculate the average rating across all books.
    
    Uses SQL's AVG() aggregate function and CAST to convert
    the text rating to a number.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    cursor.execute(
        'SELECT AVG(CAST(rating AS FLOAT)) FROM books WHERE rating != "N/A"'
    )
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result[0] else 0


def delete_book(book_id, db_name=DB_NAME):
    """
    Delete a book and its genre associations.
    
    Because we defined ON DELETE CASCADE on the book_genres table,
    deleting a book automatically removes its entries from book_genres.
    We don't need to manually clean up the junction table!
    
    CS CONCEPT: Cascading Deletes
    ─────────────────────────────
    ON DELETE CASCADE is a constraint that says:
    "When the referenced row is deleted, delete me too."
    
    Without CASCADE, trying to delete a book that has genre links
    would FAIL with a foreign key violation error.
    
    With CASCADE, it's automatic cleanup.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON;')  # Must enable for CASCADE to work
    cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
    conn.commit()
    conn.close()


def print_all_books(db_name=DB_NAME):
    """
    Print all books in the database in a readable format.
    """
    books = get_all_books(db_name)
    
    if not books:
        print("\nNo books in database yet.")
        return
    
    print(f"\n{'='*80}")
    print(f"BOOKS IN DATABASE ({len(books)} total)")
    print(f"{'='*80}\n")
    
    for book in books:
        # Each book tuple: (id, title, author_name, rating, url, scraped_at,
        #                    description, page_count, genres_string)
        book_id, title, author, rating, url, scraped_at, desc, pages, genres = book
        print(f"ID: {book_id}")
        print(f"Title: {title}")
        print(f"Author: {author}")
        print(f"Rating: {rating}")
        print(f"Pages: {pages or 'N/A'}")
        print(f"Genres: {genres or 'None'}")
        print(f"URL: {url}")
        print(f"Scraped: {scraped_at}")
        if desc:
            print(f"Description: {desc[:100]}...")
        print("-" * 80)


# ============================================================================
# ASYNC DATABASE FUNCTIONS
# ============================================================================
#
# These mirror the synchronous functions above but use aiosqlite
# for non-blocking database access in async contexts (Celery + aiohttp).
#
import aiosqlite

async def save_book_to_db_async(book_data, book_url, db_name=DB_NAME):
    """
    Asynchronously save a book with full relational linking.
    Same logic as save_book_to_db, but using aiosqlite.
    """
    try:
        async with aiosqlite.connect(db_name) as db:
            await db.execute('PRAGMA foreign_keys = ON;')
            
            # Step 1: Get or create author
            author_name = book_data.get('author', 'Unknown')
            await db.execute(
                'INSERT OR IGNORE INTO authors (name) VALUES (?)',
                (author_name,)
            )
            async with db.execute(
                'SELECT id FROM authors WHERE name = ?', (author_name,)
            ) as cursor:
                row = await cursor.fetchone()
                author_id = row[0]
            
            # Step 2: Insert/update book
            await db.execute('''
                INSERT OR REPLACE INTO books 
                    (title, author_id, rating, description, page_count, url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                book_data.get('title', 'Unknown'),
                author_id,
                book_data.get('rating', 'N/A'),
                book_data.get('description', ''),
                book_data.get('page_count'),
                book_url,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # Get book_id
            async with db.execute(
                'SELECT id FROM books WHERE url = ?', (book_url,)
            ) as cursor:
                row = await cursor.fetchone()
                book_id = row[0]
            
            # Step 3 & 4: Link genres
            await db.execute(
                'DELETE FROM book_genres WHERE book_id = ?', (book_id,)
            )
            
            genres = book_data.get('genres', [])
            for genre_name in genres:
                await db.execute(
                    'INSERT OR IGNORE INTO genres (name) VALUES (?)',
                    (genre_name,)
                )
                async with db.execute(
                    'SELECT id FROM genres WHERE name = ?', (genre_name,)
                ) as cursor:
                    row = await cursor.fetchone()
                    genre_id = row[0]
                
                await db.execute(
                    'INSERT OR IGNORE INTO book_genres (book_id, genre_id) VALUES (?, ?)',
                    (book_id, genre_id)
                )
            
            await db.commit()
            
            genre_str = ', '.join(genres[:3]) if genres else 'no genres'
            print(f"✓ Saved (Async): {book_data.get('title', 'Unknown')} [{genre_str}]")
            
    except Exception as e:
        print(f"✗ Database error (Async): {e}")