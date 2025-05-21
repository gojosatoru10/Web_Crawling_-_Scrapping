import streamlit as st
import json
import os
import csv
import pandas as pd
import plotly.express as px
import schedule
import time
import threading
from datetime import datetime, timedelta
from book_crawler_genre import main as crawl_books

def load_books_json():
    if os.path.exists('output/books.json'):
        with open('output/books.json', 'r', encoding='utf-8') as f:
            print("Loaded books from JSON.")
            return json.load(f)
    return []

def load_books_csv():
    books = []
    if os.path.exists('output/books.csv'):
        with open('output/books.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Remove 'reviews' key if present
                if 'reviews' in row:
                    del row['reviews']
                books.append(row)
    return books

def get_crawlability_score():
    allowed = 2  # /work/editions, /work/quotes
    disallowed = 6  # /book/reviews/, /review/list, /review/show, /search, /work (root), /api
    total = allowed + disallowed
    score = allowed / total if total else 0
    return score, allowed, disallowed

def get_last_crawl_time():
    """Get the timestamp of the last successful crawl"""
    if os.path.exists('output/last_crawl.txt'):
        with open('output/last_crawl.txt', 'r') as f:
            return f.read().strip()
    return "Never"

def run_scheduler():
    """Background thread to run the scheduler"""
    print("Scheduler thread started...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"Error in scheduler: {str(e)}")

def get_next_run_time():
    """Get the next scheduled run time and format it"""
    next_run = schedule.next_run()
    if next_run:
        now = datetime.now()
        time_diff = next_run - now
        if time_diff.total_seconds() < 0:
            return "No upcoming runs scheduled"
        
        # Format the time difference
        if time_diff.days > 0:
            return f"{next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {time_diff.days} days, {time_diff.seconds//3600} hours)"
        elif time_diff.seconds >= 3600:
            return f"{next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {time_diff.seconds//3600} hours, {(time_diff.seconds%3600)//60} minutes)"
        else:
            return f"{next_run.strftime('%Y-%m-%d %H:%M:%S')} (in {time_diff.seconds//60} minutes)"
    return "No upcoming runs scheduled"

def perform_crawl():
    """Execute the complete book crawling process by running book_crawler_genre.py's main function"""
    try:
        print("\n=== Starting Book Crawling Process ===")
        print("1. Creating output directory...")
        os.makedirs('output', exist_ok=True)
        
        print("2. Running book_crawler_genre.py main process...")
        # This will execute the entire process from book_crawler_genre.py
        # It will:
        # - Parse local genre sitemap
        # - Find allowed genre URLs
        # - Crawl 5 books per genre
        # - Extract book data
        # - Save to JSON and CSV
        print("Calling crawl_books() function...")
        crawl_books()  # This calls the main() function from book_crawler_genre.py
        print("crawl_books() function completed")
        
        print("3. Verifying output files...")
        if os.path.exists('output/books.json') and os.path.exists('output/books.csv'):
            print("4. Updating last crawl time...")
            with open('output/last_crawl.txt', 'w') as f:
                f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            print("=== Book Crawling Process Completed Successfully ===\n")
            return True
        else:
            print("Error: Output files were not created!")
            return False
    except Exception as e:
        print(f"Error during book crawling process: {str(e)}")
        import traceback
        print("Full error traceback:")
        print(traceback.format_exc())
        return False

def main():
    st.title('Goodreads Book Crawler Dashboard')
    
    # Initialize session state for crawl status
    if 'crawl_status' not in st.session_state:
        st.session_state.crawl_status = "Not started"
    
    # Add scheduling controls
    st.sidebar.header('Book Crawling Schedule')
    
    # Last crawl information
    last_crawl = get_last_crawl_time()
    st.sidebar.info(f"Last crawl: {last_crawl}")
    
    # Schedule controls
    schedule_type = st.sidebar.selectbox(
        'Schedule Type',
        ['Manual', 'Daily', 'Weekly', 'Custom', 'Minutes']
    )
    
    if schedule_type == 'Manual':
        if st.sidebar.button('Run Book Crawler Now'):
            print("Manual crawl button clicked")
            st.session_state.crawl_status = "Running"
            with st.spinner('Running book_crawler_genre.py process... This may take several minutes.'):
                print("Starting manual crawl process...")
                if perform_crawl():
                    st.session_state.crawl_status = "Completed"
                    st.sidebar.success('Book crawling completed successfully! Check the console for details.')
                    st.rerun()
                else:
                    st.session_state.crawl_status = "Failed"
                    st.sidebar.error('Book crawling failed. Check the console for details.')
    
    elif schedule_type == 'Daily':
        daily_time = st.sidebar.time_input('Crawl Time', datetime.now().time())
        if st.sidebar.button('Set Daily Schedule'):
            print(f"Setting daily schedule for {daily_time}")
            schedule.every().day.at(daily_time.strftime('%H:%M')).do(perform_crawl)
            st.sidebar.success(f'Daily book crawling scheduled for {daily_time.strftime("%H:%M")}')
    
    elif schedule_type == 'Weekly':
        weekday = st.sidebar.selectbox('Day of Week', 
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
        weekly_time = st.sidebar.time_input('Crawl Time', datetime.now().time())
        if st.sidebar.button('Set Weekly Schedule'):
            print(f"Setting weekly schedule for {weekday} at {weekly_time}")
            getattr(schedule.every(), weekday.lower()).at(weekly_time.strftime('%H:%M')).do(perform_crawl)
            st.sidebar.success(f'Weekly book crawling scheduled for {weekday} at {weekly_time.strftime("%H:%M")}')
    
    elif schedule_type == 'Custom':
        interval_type = st.sidebar.selectbox('Interval Type', ['Hours', 'Days'])
        if interval_type == 'Hours':
            interval = st.sidebar.number_input('Hours between crawls', min_value=1, max_value=24, value=6)
            if st.sidebar.button('Set Custom Schedule'):
                print(f"Setting custom schedule for every {interval} hours")
                schedule.every(interval).hours.do(perform_crawl)
                st.sidebar.success(f'Custom schedule set for book crawling every {interval} hours')
        else:
            interval = st.sidebar.number_input('Days between crawls', min_value=1, max_value=30, value=1)
            if st.sidebar.button('Set Custom Schedule'):
                print(f"Setting custom schedule for every {interval} days")
                schedule.every(interval).days.do(perform_crawl)
                st.sidebar.success(f'Custom schedule set for book crawling every {interval} days')
    
    elif schedule_type == 'Minutes':
        minutes = st.sidebar.number_input('Minutes between crawls', min_value=1, max_value=60, value=30)
        if st.sidebar.button('Set Minute Schedule'):
            print(f"Setting schedule for every {minutes} minutes")
            schedule.every(minutes).minutes.do(perform_crawl)
            st.sidebar.success(f'Custom schedule set for book crawling every {minutes} minutes')
    
    # Start the scheduler in a background thread
    if not hasattr(st.session_state, 'scheduler_started'):
        print("Starting scheduler thread...")
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        st.session_state.scheduler_started = True
        print("Scheduler thread started successfully")
    
    # Display crawl status and next scheduled run
    st.sidebar.info(f"Current crawl status: {st.session_state.crawl_status}")
    next_run_time = get_next_run_time()
    st.sidebar.info(f"Next scheduled crawl: {next_run_time}")
    
    # Rest of your existing dashboard code...
    st.markdown('''
    **Crawlability Summary:**
    - Allowed: `/work/editions`, `/work/quotes`
    - Disallowed: `/book/reviews/`, `/review/list`, `/review/show`, `/search`, `/work` (root), `/api`, ...
    - Sitemaps available for discovery.
    ''')
    # Crawlability Score
    score, allowed, disallowed = get_crawlability_score()
    st.subheader('Crawlability Score')
    st.progress(score)
    st.write(f"Allowed paths: {allowed}, Disallowed paths: {disallowed}")
    # Load books
    books_json = load_books_json()
    books_csv = load_books_csv()
    books = books_json if books_json else books_csv
    if not books:
        st.warning('No book data found. Please run the book extractor script first.')
        return
    # Top Extracted Data
    st.header('Top Extracted Books by Rating')
    df = pd.DataFrame(books)
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    # Remove duplicate books based on title and author
    df = df.drop_duplicates(subset=['title', 'author'])
    top_books = df.sort_values(by='rating', ascending=False).head(10)
    st.dataframe(top_books[['title', 'author', 'rating', 'genre', 'url']])
    # Display raw JSON data (first 5 books) as a table
    st.header('Sample Book Data (Table)')
    if books_json:
        sample_df = pd.DataFrame(books_json[:5])
        st.dataframe(sample_df)
    else:
        st.info('No JSON data to display.')
    # Recommendations for crawling tools
    st.header('Recommendations for Crawling Tools')
    st.markdown('''
    - Goodreads is JavaScript-heavy. Use Selenium (as implemented) or Playwright for dynamic content.
    - Always respect robots.txt and crawl allowed paths only.
    - Check for RSS feeds on genre/author pages for lighter crawling.
    - Schedule regular crawls and consider storing data in a database for scalability.
    ''')
    # Visual Sitemap (if genre URLs available)
    genre_urls = []
    if books_json:
        for book in books_json:
            if 'genre' in book and book['genre']:
                genre_urls.append(book['genre'])
    if genre_urls:
        st.header('Visual Sitemap (Genres)')
        unique_genres = list(set(genre_urls))
        dot = 'digraph sitemap {\n"Goodreads" -> {' + ' '.join(f'"{g}"' for g in unique_genres) + '}\n}'
        st.graphviz_chart(dot)
    # Book Recommendations
    st.header('Book Recommendations')
    for _, book in top_books.iterrows():
        st.subheader(book.get('title', 'Unknown Title'))
        st.write(f"**Author:** {book.get('author', 'Unknown')}")
        rating_val = book.get('rating', None)
        if pd.notnull(rating_val):
            st.write(f"**Rating:** {rating_val}")
            if float(rating_val) > 2.5:
                st.success('Recommended to read')
            else:
                st.error('Not recommended to read')
        else:
            st.write("**Rating:** Not available")
        st.write(f"[View on Goodreads]({book.get('url', '#')})")
        st.markdown('---')
    st.info('Recommendations: Use sitemaps for discovery. Only crawl allowed paths. For more data, schedule regular crawls and consider storing in a database.')

    # Top Rated Books by Genre
    st.header('Top Rated Books by Genre')
    if not df.empty:
        # Group by genre and get the highest rated book for each
        top_by_genre = df.sort_values('rating', ascending=False).groupby('genre').first().reset_index()
        
        # Create a bar chart using plotly
        fig = px.bar(top_by_genre, 
                    x='genre', 
                    y='rating',
                    title='Highest Rated Book in Each Genre',
                    labels={'genre': 'Genre', 'rating': 'Rating'},
                    hover_data=['title', 'author'])
        
        # Customize the layout
        fig.update_layout(
            xaxis_title="Genre",
            yaxis_title="Rating",
            showlegend=False,
            height=500
        )
        
        # Display the chart
        st.plotly_chart(fig, use_container_width=True)
        
        # Display the data in a table below the chart
        st.subheader('Top Rated Books by Genre Details')
        st.dataframe(top_by_genre[['genre', 'title', 'author', 'rating']])

if __name__ == "__main__":
    main()
