from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import json
import spacy
import re

print("Starting Search Service...")
app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:443",
]

print("Enabling Cors.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["get", "post"],
    allow_headers=["*"],
)
app.mount("/src", StaticFiles(directory="src"), name="src")

print("Importing necessary libraries...")

print("Loading NLP model...")
nlp = spacy.load("en_core_web_lg")
print("NLP model loaded.")

index_file = "./indexing.json"
Site_Data_Json_file = "Site_Data.json"

index_data = {}
print(f"Loading index data from {index_file}...")
try:
    with open(index_file, "r") as f:
        index_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print("Index file not found or is empty/invalid. with err ", e)


def get_context(text, keyword, window_size=10):
    """
    Extract context around keyword in raw text
    Returns the first match with surrounding words
    """
    words = text.split()
    for i, word in enumerate(words):
        if keyword.lower() in word.lower():
            start = max(0, i - window_size)
            end = min(len(words), i + window_size + 1)
            return " ".join(words[start:end])
    return None


def remove_filler_words(text):
    doc = nlp(text)
    meaningful_words = [
        token.lemma_.lower()
        for token in doc
        if token.pos_ in ["NOUN", "VERB", "ADJ", "ADV", "PROPN"] and not token.is_stop
    ]
    return meaningful_words

def lemmatization(text):
    doc = nlp(text)
    meaningful_words = [
        token.lemma_.lower()
        for token in doc
    ]
    return " ".join(meaningful_words)


def search(query, count=10):
    global index_data
    query_words = remove_filler_words(query.strip())
    results = set()

    print("Searching for:", query_words)

    if not query_words:
        return []

    # Find intersection of sites containing all query words
    initial_set = None
    for word in query_words:
        if word in index_data:
            sites = set(index_data[word])
            if initial_set is None:
                initial_set = sites
            else:
                initial_set &= sites

    if not initial_set:
        initial_set = set()

    # If not enough exact matches, add partial matches
    if len(initial_set) < count:
        for word in query_words:
            if word in index_data:
                sites = set(index_data[word])
                initial_set.update(sites)
    if len(initial_set) < count:
        print("we should find results from descs")

    results = list(initial_set)[:count]

    # Load site data for descriptions
    site_data = {}
    try:
        with open(Site_Data_Json_file, "r") as f:
            site_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Site data file not found or is empty/invalid.")

    site_descs = {}
    for site in results:
        if site in site_data:
            raw_text = site_data[site].get("words", "")
            # Try each query word until we find a match
            for word in query_words:
                context = get_context(raw_text, word)
                if context:
                    site_descs[site] = context
                    break
            # If no context found with any word
            if site not in site_descs:
                # Use beginning of text as fallback
                site_descs[site] = " ".join(raw_text.split()[:20]) + "..."
        else:
            site_descs[site] = "No content available"

    site_titles = {}
    for site in results:
        if site in site_data:
            # Get title from site_data if available, otherwise use URL
            title = site_data[site].get("title", None)
            if not title:
                # Fallback: Use the last part of URL as title
                title = site.split('/')[-1]
                if not title:  # If URL ends with /
                    title = site.split('/')[-2]
                title = title.replace('-', ' ').replace('_', ' ').title()
            site_titles[site] = title
        else:
            site_titles[site] = "Untitled Page"

    # Sort by popularity
    visited_file = "./visited_urls.json"
    visited_data = {}
    try:
        with open(visited_file, "r") as f:
            visited_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Visited file not found or is empty/invalid.")

    results = sorted(results, key=lambda site: visited_data.get(site, 0), reverse=True)

    return [results, site_descs, site_titles]


@app.post("/search")
def main(query: str, count: int = 20):
    if not query:
        raise HTTPException(status_code=404, detail="No Query Specified.")

    try:
        results, descriptions, titles = search(query, count)
        if not results:
            raise ValueError
    except (ValueError) as e:
        print(f"Err just occured {e}. prob cuz we dont have that indexed")
        raise HTTPException(status_code=418, detail="Item not found")
    full_results = {}
    for site in results:
        full_results[site] = {"description" : descriptions.get(site, "No description available"), "title" : titles.get(site, "No Title")}

    return json.dumps(full_results, indent=4)


@app.post("/nlp")
def nlp_server(query: str):
    return lemmatization(query)


@app.get("/", response_class=HTMLResponse)
def index():
    html_content = ""
    with open("src/index.html", "r") as fp:
        html_content = fp.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/search", response_class=HTMLResponse)
def searchHTML():
    html_content = ""
    with open("src/search.html", "r") as fp:
        html_content = fp.read()
    return HTMLResponse(content=html_content, status_code=200)


# @app.exception_handler(404)
# async def Page_404(_, __):
#     return RedirectResponse("/")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
