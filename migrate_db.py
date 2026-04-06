# ============================================================================
# DATABASE MIGRATION SCRIPT
# ============================================================================
#
# CS CONCEPT: Data Migration
#
# In the real world, databases don't start perfect. Requirements change,
# and you need to evolve your schema over time. This is called "migration."
#
# The challenge: you have EXISTING DATA in the old format that needs to
# be transformed into the NEW format — without losing anything.
#
# This script handles that transformation:
#   Old: 1 flat table (books with author name as text)
#   New: 4 normalized tables (authors, books, genres, book_genres)
#
# PRODUCTION NOTE:
# In real-world projects, you'd use a migration tool like:
#   - Alembic (Python/SQLAlchemy)
#   - Django Migrations
#   - Flyway (Java)
#   - Knex Migrations (Node.js)
#
# These tools track which migrations have been applied and can roll them
# back if something goes wrong. For learning, we do it manually.
#
# ============================================================================

import sqlite3
import shutil
import os
from datetime import datetime
from db import init_database, DB_NAME

# ============================================================================
# CONFIGURATION
# ============================================================================

OLD_DB = DB_NAME              # The existing flat database
BACKUP_DB = 'goodreads_books_backup.db'  # Backup of the old database


def migrate():
    """
    Migrate data from the old flat schema to the new normalized schema.
    
    Steps:
      1. Back up the old database (safety first!)
      2. Read all data from the old flat table
      3. Delete the old database
      4. Create the new normalized schema
      5. Insert each book into the normalized structure
      6. Print a summary
    """
    
    # ── Step 1: Back up ──────────────────────────────────────────────────
    #
    # GOLDEN RULE: Always back up before a destructive migration.
    # If something goes wrong, you can restore from the backup.
    #
    print("=" * 60)
    print("DATABASE MIGRATION: Flat → Normalized")
    print("=" * 60)
    
    if not os.path.exists(OLD_DB):
        print(f"\n✗ No existing database found at '{OLD_DB}'.")
        print("  Nothing to migrate. Run init_database() to create a fresh one.")
        return
    
    print(f"\n[1/5] Backing up '{OLD_DB}' → '{BACKUP_DB}'...")
    shutil.copy2(OLD_DB, BACKUP_DB)
    print(f"  ✓ Backup created: {BACKUP_DB}")
    
    # ── Step 2: Read old data ────────────────────────────────────────────
    print(f"\n[2/5] Reading data from old database...")
    
    conn = sqlite3.connect(BACKUP_DB)
    cursor = conn.cursor()
    
    # Check if this is actually the old schema (has 'author' column, not 'author_id')
    cursor.execute("PRAGMA table_info(books)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'author_id' in columns:
        print("  ⚠ Database already appears to be in the new normalized format.")
        print("  Skipping migration.")
        conn.close()
        return
    
    if 'author' not in columns:
        print(f"  ✗ Unexpected schema. Columns found: {columns}")
        conn.close()
        return
    
    cursor.execute('SELECT id, title, author, rating, url, scraped_at FROM books')
    old_books = cursor.fetchall()
    conn.close()
    
    print(f"  ✓ Found {len(old_books)} books to migrate")
    
    # ── Step 3: Delete old database ──────────────────────────────────────
    print(f"\n[3/5] Removing old database (backup saved)...")
    os.remove(OLD_DB)
    # Also remove WAL and SHM files if they exist
    for suffix in ['-wal', '-shm']:
        path = OLD_DB + suffix
        if os.path.exists(path):
            os.remove(path)
    print(f"  ✓ Old database removed")
    
    # ── Step 4: Create new schema ────────────────────────────────────────
    print(f"\n[4/5] Creating new normalized schema...")
    init_database(OLD_DB)
    
    # ── Step 5: Migrate data ─────────────────────────────────────────────
    #
    # CS CONCEPT: Batch Processing
    #
    # We process all books inside a single transaction for performance.
    # Each individual INSERT is fast, but the COMMIT (writing to disk)
    # is slow. By wrapping everything in one transaction, we only
    # commit once at the end instead of 55 times.
    #
    print(f"\n[5/5] Migrating {len(old_books)} books...")
    
    conn = sqlite3.connect(OLD_DB)
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys = ON;')
    
    migrated_count = 0
    authors_created = set()  # Track unique authors we encounter
    
    for old_book in old_books:
        old_id, title, author_name, rating, url, scraped_at = old_book
        
        try:
            # Get or create author
            cursor.execute(
                'INSERT OR IGNORE INTO authors (name) VALUES (?)',
                (author_name,)
            )
            cursor.execute(
                'SELECT id FROM authors WHERE name = ?',
                (author_name,)
            )
            author_id = cursor.fetchone()[0]
            authors_created.add(author_name)
            
            # Insert book with the new schema
            # Note: description, page_count, and genres are empty for migrated
            # books since the old scraper didn't collect them. You can re-scrape
            # to fill these in later.
            cursor.execute('''
                INSERT OR REPLACE INTO books 
                    (title, author_id, rating, description, page_count, url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                title,
                author_id,
                rating,
                '',          # description — not available in old data
                None,        # page_count — not available in old data
                url,
                scraped_at   # Preserve original scrape timestamp
            ))
            
            migrated_count += 1
            
        except sqlite3.Error as e:
            print(f"  ✗ Failed to migrate '{title}': {e}")
    
    conn.commit()
    conn.close()
    
    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"MIGRATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Books migrated:    {migrated_count}/{len(old_books)}")
    print(f"  Authors created:   {len(authors_created)}")
    print(f"  Genres:            0 (re-scrape to populate)")
    print(f"  Backup location:   {BACKUP_DB}")
    print(f"\n  To fill in missing genres/descriptions, re-scrape your books.")
    print(f"  The backup of your old database is at: {BACKUP_DB}")


if __name__ == '__main__':
    migrate()
