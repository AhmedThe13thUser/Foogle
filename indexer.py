import requests
from bs4 import BeautifulSoup
import re
import spacy
import json
import os
import threading
from queue import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed

print("Loading NLP model...")
nlp = spacy.load("en_core_web_lg")
print("NLP model loaded.")

EN_Headers = {
    "Accept-Language": "en-US,en;q=0.9",
}

# Configuration
NUM_WORKERS = 100  # Number of worker threads
Visited_Urls_text_file = input("File to index URLS from: ") or "visited_urls.txt"
Indexed_Urls_text_file = "./Indexed_Urls.txt"
Site_Data_Json_file = "./Site_Data.json"
index_file = "./indexing.json"

# Thread-safe data structures and locks
url_queue = Queue()
index_lock = threading.Lock()
file_lock = threading.Lock()
indexed_urls = set()
index_data = {}
urls_Saved_no = [0]
urls_Indexed_no = [0]


if os.path.exists(index_file):
    os.remove(index_file)
if os.path.exists(Site_Data_Json_file):
    os.remove(Site_Data_Json_file)
if os.path.exists(Indexed_Urls_text_file):
    os.remove(Indexed_Urls_text_file)




# Load existing data | THIS FEATURE IS DEPRECATED AND I DONT WANT TO REMOVE IT AND REFACTOR THE CODE
def load_existing_data():
    global index_data, indexed_urls
    
    continuing = False
    if os.path.exists(Indexed_Urls_text_file) and os.path.exists(index_file):
        print("Continuing where we left off...")
        continuing = True
    
    with open(Visited_Urls_text_file, "r", encoding="utf8") as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]
        print(f"Loaded {len(urls)} URLs from {Visited_Urls_text_file}")
    
    if continuing:
        with open(index_file, "r", encoding="utf8") as f:
            index_data = json.load(f)
            print(f"Loaded existing index data with {len(index_data)} words")
        
        with open(Indexed_Urls_text_file, "r", encoding="utf8") as f:
            indexed_urls = set(line.strip() for line in f.readlines())
            print(f"Loaded {len(indexed_urls)} already indexed URLs")
    
    # Add only unindexed URLs to the queue
    new_urls = [url for url in urls if url not in indexed_urls]
    print(f"Found {len(new_urls)} new URLs to index")
    
    for url in new_urls:
        url_queue.put(url)

def save_index_data():
    print(f"Saving index data... for url Saved no. ${urls_Saved_no[0]}")
    with file_lock:
        with open(index_file, "w", encoding="utf8") as f:
            json.dump(index_data, f, indent=4)
        
        with open(Indexed_Urls_text_file, "w", encoding="utf8") as f:
            for url in indexed_urls:
                f.write(url + "\n")
        urls_Saved_no[0] += 1

def inverted_indexing(data):
    global index_data
    
    # Index title words
    for word in str(data["title"]).lower().split():
        if not word.isalpha():
            continue
        with index_lock:
            if word in index_data:
                if data["url"] not in index_data[word]:
                    index_data[word].append(data["url"])
            else:
                index_data[word] = [data["url"]]
    
    # Index description words
    for word in str(data["description"]).lower().split():
        if not word.isalpha():
            continue
        with index_lock:
            if word in index_data:
                if data["url"] not in index_data[word]:
                    index_data[word].append(data["url"])
            else:
                index_data[word] = [data["url"]]
    
    # Index content words
    for word in str(data["words"]).lower().split():
        if not word.isalpha():
            continue
        with index_lock:
            if word in index_data:
                if data["url"] not in index_data[word]:
                    index_data[word].append(data["url"])
            else:
                index_data[word] = [data["url"]]
    
    # Periodically save data
    if len(index_data) % 10 == 0:
        save_index_data()

def process_site_data(url, data):
    with file_lock:
        site_data = {}
        if os.path.exists(Site_Data_Json_file):
            try:
                with open(Site_Data_Json_file, "r", encoding="utf8") as f:
                    site_data = json.load(f)
            except:
                print(f"{Site_Data_Json_file} is empty or corrupted, starting fresh")
        
        site_data[url] = {
            "title": data["title"],
            "words": data["words"],
        }
        
        with open(Site_Data_Json_file, "w", encoding="utf8") as f:
            json.dump(site_data, f, indent=4)

def index_url(url):
    if url in indexed_urls:
        print(f"Already indexed: {url}")
        return False
    
    try:
        response = requests.get(url, headers=EN_Headers, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        title = soup.title.string if soup.title else "No Title"
        
        # Get meta description or first 200 characters of text
        description = ""
        meta_description = soup.find("meta", attrs={"name": "description"})
        if meta_description and "content" in meta_description.attrs:
            description = meta_description["content"]
        else:
            text_content = soup.get_text(separator=" ", strip=True)[:200]
            description = (text_content[:200] + "..." if len(text_content) > 200 
                          else text_content)

        # Extract and filter words
        words_notfiltered = re.findall(
            r"\b\w+\b", soup.get_text(separator=" ", strip=True).lower()
        )
        words_notfiltered = [word for word in words_notfiltered if word.isalpha()]
        words_notfiltered = " ".join(words_notfiltered)

        # Remove stop words
        words = []
        for item in nlp(words_notfiltered):
            if not item.is_stop:
                words.append(item.text)
        words = " ".join(words)
        words = re.sub(r"[^a-zA-Z0-9\s]", "", words)

        # Create indexed data structure
        indexed_data = {
            "url": url,
            "title": title,
            "description": description,
            "words": words,
        }

        # Save site data
        process_site_data(url, indexed_data)
        
        # Add to inverted index
        inverted_indexing(indexed_data)
        
        # Mark URL as indexed
        with index_lock:
            indexed_urls.add(url)
        
        print(f"Successfully indexed: {url} and this is url no. {urls_Indexed_no} to be indexed.")
        urls_Indexed_no[0] += 1
        return True
    
    except requests.RequestException as e:
        print(f"Failed to index {url}: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error indexing {url}: {e}")
        return False

def worker():
    while True:
        url = url_queue.get()
        if url is None:  # Sentinel value to exit
            break
        
        index_url(url)
        url_queue.task_done()

def start():
    load_existing_data()
    
    print(f"Starting {NUM_WORKERS} worker threads...")
    workers = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker)
        t.start()
        workers.append(t)
    
    # Wait for all URLs to be processed
    url_queue.join()
    
    # Stop workers
    for _ in range(NUM_WORKERS):
        url_queue.put(None)
    for t in workers:
        t.join()
    
    # Final save
    save_index_data()
    print("Indexing complete!")

if __name__ == "__main__":
    start()