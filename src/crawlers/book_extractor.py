import requests
import time
import json
import csv
from parse_local_genre_xml import get_genre_pages_from_local_xml
from book_crawler_genre import extract_book_data

def fetch_sample_book_editions_urls():
    # Dummy implementation: you should replace this with actual logic to fetch edition URLs
    genre_urls = get_genre_pages_from_local_xml()
    edition_urls = []
    for genre_url in genre_urls:
        # For demo, just use the genre page as a placeholder
        edition_urls.append(genre_url)
    return edition_urls

def main():
    print("Fetching sample /work/editions URLs from sitemap...")
    edition_urls = fetch_sample_book_editions_urls()
    print(f"Found {len(edition_urls)} edition URLs. Extracting book data...")
    books = []
    for url in edition_urls:
        try:
            data = extract_book_data(url)
            # Remove 'reviews' key if present
            if 'reviews' in data:
                del data['reviews']
            books.append(data)
            print(f"Extracted: {data['title']} by {data['author']}")
            time.sleep(5)  # Polite delay between requests
        except Exception as e:
            print(f"Failed to extract {url}: {e}")
    # Save to JSON for use in Streamlit
    with open('output/books.json', 'w', encoding='utf-8') as f:
        json.dump(books, f, ensure_ascii=False, indent=2)
    print("Book data saved to output/books.json.")
    # Save to CSV as well
    with open('output/books.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'author', 'url', 'description', 'rating', 'genre'])
        writer.writeheader()
        for book in books:
            # Remove 'reviews' key if present
            book_out = {k: v for k, v in book.items() if k != 'reviews'}
            writer.writerow(book_out)
    print("Book data saved to output/books.csv.")

if __name__ == "__main__":
    main()
