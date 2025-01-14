import os
import json
import requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify, render_template
from sentence_transformers import SentenceTransformer, util

# Initialize Flask app
app = Flask(__name__)

# Initialize SentenceTransformer for semantic search
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Base URLs for scraping
BASE_URLS = {
    "Segment": "https://segment.com/docs/?ref=nav",
    "mParticle": "https://docs.mparticle.com/",
    "Lytics": "https://docs.lytics.com/",
    "Zeotap": "https://docs.zeotap.com/home/en-us/"
}

# Storage for scraped data
DOCUMENTATION = {}


# Step 1: Web Scraping
def scrape_documentation(url, base_url, depth=2):
    visited_links = set()
    data = []

    def scrape_page(link, current_depth):
        if current_depth > depth or link in visited_links or not link.startswith(base_url):
            return
        visited_links.add(link)
        print(f"Scraping: {link}")  # Add print statement to see scraping progress
        try:
            response = requests.get(link)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title and content
            title = soup.title.string if soup.title else "No Title"
            content = ' '.join([p.text for p in soup.find_all('p')])
            data.append({"url": link, "title": title, "content": content})

            # Find and scrape internal links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if href.startswith('/'):
                    href = base_url + href
                scrape_page(href, current_depth + 1)

        except Exception as e:
            print(f"Error scraping {link}: {e}")

    scrape_page(url, 1)
    return data


# Step 2: Scrape and Index Data
def scrape_all_documentation():
    global DOCUMENTATION
    for name, url in BASE_URLS.items():
        DOCUMENTATION[name] = scrape_documentation(url, url)
    # Save to JSON for future use
    with open('documentation.json', 'w') as f:
        json.dump(DOCUMENTATION, f, indent=2)


def load_data():
    # Check if the file exists
    if os.path.exists('documentation.json'):
        with open('documentation.json', 'r') as f:
            DOCUMENTATION = json.load(f)
    else:
        print("No documentation file found.")
        return []

    # Load data into contents
    contents = []
    for source, docs in DOCUMENTATION.items():
        for doc in docs:
            # Safely extract data and avoid truncation
            contents.append({
                "source": source,
                "url": doc.get("url", "No URL Provided"),
                "title": doc.get("title", "No Title Provided"),
                "content": doc.get("content", "No Content Available").strip(),
            })

    return contents

# Example of usage
data = load_data()
for item in data:
    print("Source:", item["source"])
    print("URL:", item["url"])
    print("Title:", item["title"])
    print("Content:", item["content"])  # Prints full content
    print("-" * 80)

from flask import Flask, render_template, redirect, url_for
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Login logic here (process the form submission)
        return redirect(url_for('home'))  # Redirect to home after login
    return render_template('login.html')
@app.route('/signup', methods=['POST'])
def signup():
    # Signup logic here
    return redirect(url_for('home'))
# Step 4: Search Functionality
def search_query(query, contents):
    print(f"Query received: {query}")  # Add print statement to see the query
    query_embedding = embedding_model.encode(query, convert_to_tensor=True)

    # Create embeddings for document contents
    doc_embeddings = embedding_model.encode([doc['content'] for doc in contents], convert_to_tensor=True)

    # Compute cosine similarities between query and all documents
    cosine_scores = util.pytorch_cos_sim(query_embedding, doc_embeddings)[0]

    # Get the index of the best matching document
    best_match_index = cosine_scores.argmax()

    # Prepare the response with the relevant paragraph
    best_match_doc = contents[best_match_index]
    return {
        "title": best_match_doc['title'],
        "source": best_match_doc['source'],
        "url": best_match_doc['url'],
        "content": best_match_doc['content']  # Limit the content length
    }


# Step 5: Flask Routes
@app.route('/')
def home():
    return render_template('index.html')  # Adjust if needed

# Chat page route
@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/query', methods=['POST'])
def query():
    user_query = request.json.get('query', '')
    print(f"Received query: {user_query}")  # Add print statement to see the query

    if not user_query:
        return jsonify({"error": "Query cannot be empty"}), 400

    # Load the scraped data (or use an existing JSON)
    contents = load_data()

    # Get search result
    result = search_query(user_query, contents)
    print(f"Search result: {result}")  # Add print statement to see the result

    # Check if the result is empty
    if not result or result.get("content") == "undefined":
        return jsonify({"response": "I'm trained to provide answers only related to customer data platform (CDP) topics."}), 200

    return jsonify(result)
# Initialize
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Get the port number from the environment variable or default to 5000
    app.run(host='0.0.0.0', port=port)
