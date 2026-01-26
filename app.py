from flask import Flask, render_template, redirect, url_for, request, flash
from db import get_all_books, get_average_rating, init_database
# Import the Celery task instead of the synchronous pipeline function
from tasks import scrape_list_task 
from db import delete_book 

app = Flask(__name__)
# Required for session/flash messaging
app.secret_key = 'super_secret_key_for_dev'

# Initialize DB on startup so tables exist
init_database()

@app.route('/')
def index():
    books = get_all_books() #
    avg_rating = get_average_rating() #
    return render_template('index.html', books=books, avg_rating=avg_rating)

@app.route('/scrape', methods=['POST'])
def run_scraper():
    # Define the URL you want to scrape
    list_url = "https://www.goodreads.com/list/show/1.Best_Books_Ever"
    
    # Hand off the task to Celery!
    # .delay() is the magic method that sends the message to Redis
    # The browser gets an immediate response while the worker runs in the background
    task = scrape_list_task.delay(list_url, limit=5)
    
    flash(f"Started background scrape! Task ID: {task.id}", "info")
    
    return redirect(url_for('index'))

@app.route('/delete/<int:book_id>', methods=['POST'])
def remove_entry(book_id):
    delete_book(book_id)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)