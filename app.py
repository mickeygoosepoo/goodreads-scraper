from flask import Flask, render_template, redirect, url_for, request, flash
from db import (
    get_all_books, get_average_rating, init_database,
    delete_book, get_books_by_author, get_books_by_genre, get_genre_stats
)
# Import the Celery task instead of the synchronous pipeline function
from tasks import scrape_list_task 

app = Flask(__name__)
# Required for session/flash messaging
app.secret_key = 'super_secret_key_for_dev'

# Initialize DB on startup so tables exist
init_database()

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """
    Main dashboard — shows all books, average rating, and genre stats.
    """
    books = get_all_books()
    avg_rating = get_average_rating()
    genre_stats = get_genre_stats()  # NEW: genre breakdown for sidebar
    return render_template(
        'index.html', 
        books=books, 
        avg_rating=avg_rating,
        genre_stats=genre_stats,
        filter_type=None,        # No active filter on the main page
        filter_value=None
    )


@app.route('/author/<author_name>')
def books_by_author(author_name):
    """
    Filtered view — shows only books by a specific author.
    
    CS CONCEPT: Parameterized Routes
    ──────────────────────────────────
    <author_name> in the URL pattern is a "URL parameter."
    Flask extracts the value and passes it to the function.
    
    Example: /author/Matt%20Haig → author_name = "Matt Haig"
    
    The %20 is URL encoding for a space character. Flask handles
    decoding this automatically.
    """
    books = get_books_by_author(author_name)
    avg_rating = get_average_rating()
    genre_stats = get_genre_stats()
    return render_template(
        'index.html',
        books=books,
        avg_rating=avg_rating,
        genre_stats=genre_stats,
        filter_type='author',
        filter_value=author_name
    )


@app.route('/genre/<genre_name>')
def books_by_genre(genre_name):
    """
    Filtered view — shows only books in a specific genre.
    Uses the junction table query (books → book_genres → genres).
    """
    books = get_books_by_genre(genre_name)
    avg_rating = get_average_rating()
    genre_stats = get_genre_stats()
    return render_template(
        'index.html',
        books=books,
        avg_rating=avg_rating,
        genre_stats=genre_stats,
        filter_type='genre',
        filter_value=genre_name
    )


@app.route('/scrape', methods=['POST'])
def run_scraper():
    """
    Trigger a background scrape via Celery.
    """
    list_url = "https://www.goodreads.com/list/show/1.Best_Books_Ever"
    
    # .delay() sends the task to Celery (Redis) for background execution
    task = scrape_list_task.delay(list_url, limit=5)
    
    flash(f"Started background scrape! Task ID: {task.id}", "info")
    
    return redirect(url_for('index'))


@app.route('/delete/<int:book_id>', methods=['POST'])
def remove_entry(book_id):
    """
    Delete a book. CASCADE handles junction table cleanup automatically.
    """
    delete_book(book_id)
    return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(debug=True)