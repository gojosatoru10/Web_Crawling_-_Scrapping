import requests
import xml.etree.ElementTree as ET
import time
from bs4 import BeautifulSoup
from typing import List
import csv
import json
from parse_local_genre_xml import get_genre_pages_from_local_xml

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; MyGoodreadsCrawler/1.0; +https://yourdomain.example)'
}

# Only keep genres matching the allowed list
allowed_genres = [
    "Thriller", "Classics", "Comics", "Fantasy", "Fiction", "Science Fiction"
]

def fetch_sitemap_urls(sitemap_url: str) -> List[str]:
    resp = requests.get(sitemap_url, headers=HEADERS)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = [url.text for url in root.findall('.//ns:url/ns:loc', ns)]
    return urls

def get_books_from_genre_page(genre_url):
    resp = requests.get(genre_url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    book_links = set()
    all_a = soup.find_all('a', href=True)
    print(f"    Found {len(all_a)} <a> tags on {genre_url}")
    for i, a in enumerate(all_a[:10]):
        print(f"      Sample href {i+1}: {a['href']}")
    for a in all_a:
        href = a['href']
        if '/book/show/' in href:
            # Normalize to full URL
            if href.startswith('http'):
                book_links.add(href.split('?')[0])
            else:
                book_links.add('https://www.goodreads.com' + href.split('?')[0])
    print(f"    Extracted {len(book_links)} book links from {genre_url}")
    return list(book_links)  # Return all found book links instead of limiting to 5

def extract_book_data(book_url: str):
    resp = requests.get(book_url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    # Robust title extraction
    title = None
    # Try old layout
    title_elem = soup.find('h1', {'id': 'bookTitle'})
    if title_elem and title_elem.text.strip():
        title = title_elem.text.strip()
    # Try new layout
    if not title:
        title_elem = soup.find('h1', {'data-testid': 'bookTitle'})
        if title_elem and title_elem.text.strip():
            title = title_elem.text.strip()
    if not title:
        h1s = soup.find_all('h1')
        for h1 in h1s:
            if h1.text.strip():
                title = h1.text.strip()
                break
    # Robust author extraction
    author = None
    author_elem = soup.find('a', {'class': 'authorName'})
    if author_elem and author_elem.text.strip():
        author = author_elem.text.strip()
    if not author:
        author_elem = soup.find('span', {'itemprop': 'author'})
        if author_elem:
            a = author_elem.find('a')
            if a and a.text.strip():
                author = a.text.strip()
    if not author:
        author_links = soup.find_all('a', href=True)
        for a in author_links:
            if '/author/show/' in a['href'] and a.text.strip():
                author = a.text.strip()
                break
    # Extract description with multiple selectors
    description = None
    desc_div = soup.find('div', {'id': 'description'})
    if desc_div:
        spans = desc_div.find_all('span')
        if len(spans) > 1 and spans[1].text.strip():
            description = spans[1].text.strip()
        elif spans:
            description = spans[0].text.strip()
    if not description:
        desc_span = soup.find('span', {'data-testid': 'description'})
        if desc_span and desc_span.text.strip():
            description = desc_span.text.strip()
    if not description:
        desc_div2 = soup.find('div', class_='BookPageMetadataSection__description')
        if desc_div2 and desc_div2.text.strip():
            description = desc_div2.text.strip()
    if not description:
        desc_div3 = soup.find('div', class_='DetailsLayoutRightParagraph__widthConstrained')
        if desc_div3 and desc_div3.text.strip():
            description = desc_div3.text.strip()
    if not description:
        try:
            main = soup.find('main')
            if main:
                divs = main.find_all('div', recursive=False)
                if len(divs) > 1:
                    div2 = divs[1]
                    divs2 = div2.find_all('div', recursive=False)
                    if len(divs2) > 1:
                        div3 = divs2[1]
                        divs3 = div3.find_all('div', recursive=False)
                        if len(divs3) > 1:
                            div4 = divs3[1]
                            divs4 = div4.find_all('div', recursive=False)
                            if len(divs4) > 4:
                                div5 = divs4[4]
                                divs5 = div5.find_all('div', recursive=False)
                                if divs5:
                                    div6 = divs5[0]
                                    divs6 = div6.find_all('div', recursive=False)
                                    if divs6:
                                        div7 = divs6[0]
                                        divs7 = div7.find_all('div', recursive=False)
                                        if divs7:
                                            div8 = divs7[0]
                                            span = div8.find('span')
                                            if span and span.text.strip():
                                                description = span.text.strip()
        except Exception:
            pass
    # Extract rating
    rating = None
    rating_elem = soup.find('span', itemprop='ratingValue')
    if rating_elem and rating_elem.text.strip():
        rating = rating_elem.text.strip()
    # Try extracting rating using the provided XPath (converted to BeautifulSoup logic)
    if not rating:
        try:
            main = soup.find('main')
            if main:
                div1 = main.find_all('div', recursive=False)[0]
                div2 = div1.find_all('div', recursive=False)[1]
                div3 = div2.find_all('div', recursive=False)[2]
                div4 = div3.find_all('div', recursive=False)[1]
                div5 = div4.find_all('div', recursive=False)[1]
                div6 = div5.find_all('div', recursive=False)[2]
                a = div6.find('a')
                if a:
                    div7 = a.find_all('div', recursive=False)[0]
                    div8 = div7.find_all('div', recursive=False)[0]
                    if div8 and div8.text.strip():
                        rating = div8.text.strip()
        except Exception:
            pass
    # Fallback: search for a float-like rating in main content near the top
    if not rating:
        import re
        main = soup.find('main')
        if main:
            # Look for divs or spans with a float value (e.g., 4.12, 3.8, etc.)
            candidates = main.find_all(['div', 'span'], string=True)
            for c in candidates:
                text = c.get_text(strip=True)
                if re.match(r'^[1-5]\.[0-9]{1,2}$', text):
                    rating = text
                    break
    # Fallback: look for common rating class names
    if not rating:
        rating_classes = ['RatingStatistics__rating', 'BookPageMetadataSection__rating', 'DetailsLayoutRightRating__value']
        for cls in rating_classes:
            elem = soup.find(class_=cls)
            if elem and elem.text.strip():
                rating = elem.text.strip()
                break
    # Extract genres (as comma-separated string)
    genres = []
    genre_links = soup.find_all('a', href=True)
    for a in genre_links:
        href = a['href']
        if '/genres/' in href and a.text.strip():
            genres.append(a.text.strip())
    # Only keep genres that exactly match allowed_genres (case-insensitive, ignoring apostrophes and spaces)
    def normalize(genre):
        return genre.lower().replace("'", "").replace(' ', '')
    allowed_normalized = {normalize(g): g for g in allowed_genres}
    filtered_genres = []
    for g in set(genres):
        norm = normalize(g)
        if norm in allowed_normalized and g.lower() == allowed_normalized[norm].lower():
            filtered_genres.append(allowed_normalized[norm])
    # Only keep the first matching genre, or None
    filtered_genres = filtered_genres[:1] if filtered_genres else []
    return {
        'url': book_url,
        'title': title,
        'author': author,
        'description': description,
        'rating': rating,
        'genre': filtered_genres[0] if filtered_genres else None
    }

def main():
    print("Parsing local genre sitemap for genre URLs...")
    genre_urls = get_genre_pages_from_local_xml()
    filtered_genre_urls = []
    for url in genre_urls:
        for genre in allowed_genres:
            # Check if genre name (case-insensitive, spaces replaced with '-') is in the URL
            genre_slug = genre.lower().replace("'", "").replace(' ', '-')
            if f"/genres/{genre_slug}" in url.lower():
                filtered_genre_urls.append(url)
                break
    print(f"Found {len(filtered_genre_urls)} allowed genre URLs. Crawling books...")
    all_books = []
    # Make a copy of allowed_genres to track which genres still need books
    genres_to_collect = allowed_genres.copy()
    genre_book_count = {g: 0 for g in allowed_genres}
    genre_completion_counter = 0  # Counter for completed genres
    total_books_extracted = 0  # Counter for successfully extracted books
    
    for genre_url in filtered_genre_urls:
        # Determine which genre this URL is for
        matched_genre = None
        for genre in genres_to_collect:
            genre_slug = genre.lower().replace("'", "").replace(' ', '-')
            if f"/genres/{genre_slug}" in genre_url.lower():
                matched_genre = genre
                break
        # Skip this URL if the matched_genre or any substring genre is already collected
        if not matched_genre:
            continue
        # Check if any collected genre is a substring of matched_genre (case-insensitive)
        skip = False
        for collected in allowed_genres:
            if collected not in genres_to_collect:
                # If the collected genre is a substring of the matched genre, skip
                if collected.lower() in matched_genre.lower() or matched_genre.lower() in collected.lower():
                    skip = True
                    break
        if skip:
            print(f"Skipping {genre_url} ({matched_genre}) because a similar genre was already collected.")
            continue
        print(f"Processing genre: {genre_url} ({matched_genre})")
        try:
            book_urls = get_books_from_genre_page(genre_url)
            print(f"  Found {len(book_urls)} books in genre.")
            
            # Keep trying to extract books until we have exactly 5 for this genre
            for url in book_urls:
                # Skip if we already have 5 books for this genre
                if genre_book_count[matched_genre] >= 5:
                    break
                    
                try:
                    data = extract_book_data(url)
                    # Only add if the book's genre matches the matched_genre
                    if data['genre'] and data['genre'].lower() == matched_genre.lower():
                        all_books.append(data)
                        genre_book_count[matched_genre] += 1
                        total_books_extracted += 1
                        print(f"    Extracted: {data['title']} by {data['author']}")
                        print(f"    Total books extracted so far: {total_books_extracted}")
                        print(f"    Books for this genre: {genre_book_count[matched_genre]}/5")
                        
                        # If we've reached exactly 5 books for this genre
                        if genre_book_count[matched_genre] == 5:
                            genres_to_collect.remove(matched_genre)
                            genre_completion_counter += 1
                            print(f"    Successfully collected exactly 5 books for genre '{matched_genre}'")
                            print(f"    Completed genres: {genre_completion_counter}/{len(allowed_genres)}")
                            break
                    time.sleep(5)
                except Exception as e:
                    print(f"    Failed to extract {url}: {e}")
                    continue
            
            # If we couldn't get exactly 5 books for this genre, remove it from collection
            if genre_book_count[matched_genre] < 5:
                print(f"    Warning: Could only extract {genre_book_count[matched_genre]} books for genre '{matched_genre}'")
                if matched_genre in genres_to_collect:
                    genres_to_collect.remove(matched_genre)
                    genre_completion_counter += 1
                    print(f"    Removing '{matched_genre}' from collection due to insufficient books")
            
            time.sleep(10)  # Extra delay between genres
            
            # Break conditions:
            # 1. When all genres have been completed
            if genre_completion_counter >= len(allowed_genres):
                print("Breaking: All genres have been processed")
                break
                
        except Exception as e:
            print(f"  Failed to process genre {genre_url}: {e}")
    
    print(f"\nCrawling Summary:")
    print(f"Total books successfully extracted: {total_books_extracted}")
    print(f"Total genres completed: {genre_completion_counter}/{len(allowed_genres)}")
    print("\nBooks per genre:")
    for genre in allowed_genres:
        print(f"{genre}: {genre_book_count[genre]} books")
    
    with open('output/books.json', 'w', encoding='utf-8') as f:
        json.dump(all_books, f, ensure_ascii=False, indent=2)
    with open('output/books.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['title', 'author', 'url', 'description', 'rating', 'genre'])
        writer.writeheader()
        for book in all_books:
            book_out = {k: v for k, v in book.items() if k != 'reviews'}
            writer.writerow(book_out)
    print("Book data saved to output/books.json and output/books.csv.")

if __name__ == "__main__":
    main()
