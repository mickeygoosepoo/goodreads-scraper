import requests
import sqlite3
import time
import sys
import redis
from datetime import datetime

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

def check_redis():
    print(f"\n[1/4] Checking Redis Connection...")
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print(f" {PASS} Redis is running and reachable.")
        return True
    except redis.ConnectionError:
        print(f" {FAIL} Could not connect to Redis. Is it running?")
        print("       Run: brew services start redis")
        return False

def check_flask():
    print(f"\n[2/4] Checking Flask Web Server...")
    try:
        response = requests.get('http://127.0.0.1:5000/')
        if response.status_code == 200:
            print(f" {PASS} Flask is up and running.")
            return True
        else:
            print(f" {FAIL} Flask returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f" {FAIL} Could not connect to Flask at http://127.0.0.1:5000")
        return False

def get_book_count():
    conn = sqlite3.connect('goodreads_books.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM books')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def check_schema():
    """Verify the normalized schema has all 4 required tables."""
    print(f"\n[1.5/4] Checking Database Schema...")
    conn = sqlite3.connect('goodreads_books.db')
    cursor = conn.cursor()
    
    required_tables = ['authors', 'books', 'genres', 'book_genres']
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = [row[0] for row in cursor.fetchall()]
    
    all_good = True
    for table in required_tables:
        if table in existing:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f" {PASS} Table '{table}' exists ({count} rows)")
        else:
            print(f" {FAIL} Table '{table}' is MISSING")
            all_good = False
    
    conn.close()
    return all_good

def trigger_and_monitor():
    print(f"\n[3/4] Triggering Scrape Task...")
    initial_count = get_book_count()
    print(f" Current Book Count: {initial_count}")
    
    try:
        # Trigger the scrape via the web endpoint
        response = requests.post('http://127.0.0.1:5000/scrape')
        if response.status_code == 200:
            print(f" {PASS} Scrape request accepted by Flask.")
        else:
            print(f" {FAIL} Scrape request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f" {FAIL} Error triggering scrape: {e}")
        return False
        
    print(f"\n[4/4] Monitoring Database for 15 seconds...")
    for i in range(15):
        current_count = get_book_count()
        if current_count > initial_count:
            print(f" {PASS} SUCCESS! New books detected in database.")
            print(f"        Books added: {current_count - initial_count}")
            return True
        sys.stdout.write(f"\r Waiting for worker... {i+1}s")
        sys.stdout.flush()
        time.sleep(1)
        
    print(f"\n\n {FAIL} Timeout: No new books appeared in the database.")
    print("       Possible causes:")
    print("       1. Celery worker is not running.")
    print("       2. Celery worker is STALE (needs restart to see new code).")
    print("       3. Redis is down.")
    return False

if __name__ == "__main__":
    print("=== DISTRIBUTED SYSTEM HEALTH CHECK ===")
    
    if not check_redis():
        sys.exit(1)
    
    if not check_schema():
        print("\n Run migrate_db.py to set up the normalized schema.")
        sys.exit(1)
        
    if not check_flask():
        sys.exit(1)
        
    trigger_and_monitor()
