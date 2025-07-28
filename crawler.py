from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue
import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import urlparse
import json
import os
from queue import Empty
import sys


starting_Urls = []

with open("starting_urls.txt", "r") as f:
    starting_Urls = [line.strip() for line in f.readlines()]

Saved_Disallowed = set()
Already_Crawled_Robots = set()
EN_Headers = {
    "Accept-Language": "en-US,en;q=0.9",
}



visited_urls_Json_File = "visited_urls.json"
visited_urls_Text_File = "visited_urls.txt"

if os.path.exists(visited_urls_Json_File):
    os.remove(visited_urls_Json_File)
if os.path.exists(visited_urls_Text_File):
    os.remove(visited_urls_Text_File)




popular_urls = {}


def can_crawl(url):
    global Saved_Disallowed, Already_Crawled_Robots, popular_urls
    if url in Saved_Disallowed:
        print(f"disallowed by robots.txt: {url}")
        return False
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    if robots_url in Already_Crawled_Robots:
        print(f"already checked robots.txt for: {robots_url}")
        return True
    Already_Crawled_Robots.add(robots_url)
    print(f"checking robots.txt for: {robots_url}")
    # time.sleep(random.uniform(1, 3))
    try:
        response = requests.get(robots_url, headers=EN_Headers, timeout=10)
        response.raise_for_status()
        disallowed_paths = []
        for line in response.text.splitlines():
            if line.startswith("Disallow"):
                parts = line.split()
                if len(parts) > 1:
                    disallowed_paths.append(parts[1])
                    # Fix 1: Ensure you're adding the actual disallowed path relative to the domain,
                    # not the full URL + path, which is unlikely to be a valid disallow rule for Saved_Disallowed
                    # Saved_Disallowed.add(url + parts[1]) # Original - incorrect
                    # Corrected: Add the combination of domain and disallowed path for clear tracking if needed
                    # Or, more simply, just track the specific URL if it's disallowed.
                    # For now, let's keep the original logic for 'Saved_Disallowed' for minimal change,
                    # but be aware of its exact meaning.
                    # The more robust solution involves storing domain -> [disallowed_paths] as suggested previously.
                    pass  # We'll just rely on the path check below for `can_crawl`
                    # and not try to save all permutations to `Saved_Disallowed` here,
                    # as it's meant to cache specific URLs found to be disallowed.

        for path in disallowed_paths:
            # Fix 2: Add the URL to Saved_Disallowed if it's found to be disallowed here.
            # It's better to add the full current_Url that was checked and disallowed.
            if urlparse(url).path.startswith(path):
                print(f"disallowed by robots.txt: {url} (matched path: {path})")
                Saved_Disallowed.add(url)  # Add the actual URL that was disallowed
                return False
        return True
    except requests.RequestException:
        print(f"failed to retrieve {robots_url}... so we can crawl it...")
        return True


def crawl(queue, visited_urls, crawl_count, crawl_limit, lock, stop_event):
    while not stop_event.is_set():
        try:
            # Check limit before processing
            with lock:
                if crawl_count[0] >= crawl_limit:
                    stop_event.set()
                    return

            # Get URL with short timeout
            try:
                current_url = queue.get(timeout=1)
            except Empty:
                continue  # Check stop_event again

            # Process the URL
            with lock:
                if crawl_count[0] >= crawl_limit:
                    queue.task_done()
                    stop_event.set()
                    return

                if current_url in visited_urls:
                    queue.task_done()
                    continue

                visited_urls.add(current_url)
                crawl_count[0] += 1
                print(
                    f"added link: {current_url} this is link number. {crawl_count[0]}"
                )

                # Update popularity
                popular_urls[current_url] = popular_urls.get(current_url, 0) + 1
                sorted_dict = {}
                print("outputing the popularity list.")
                sorted_dict = dict(
                    sorted(popular_urls.items(), key=lambda x: x[1], reverse=True)
                )
                with open("visited_urls.json", "w", encoding="utf8") as f:
                    json.dump(sorted_dict, f, indent=4)
                print("outputing the plain list with .txt format.")
                with open("visited_urls.txt", "w", encoding="utf8") as f:
                    for url, count in sorted_dict.items():
                        f.write(f"{url}\n")

            # Check robots.txt
            if not can_crawl(current_url):
                queue.task_done()
                continue

            # Fetch the page
            try:
                response = requests.get(current_url, headers=EN_Headers, timeout=10)
                if response.status_code != 200:
                    raise requests.RequestException(
                        f"Status code {response.status_code}"
                    )

                if "noindex" in response.text.lower():
                    queue.task_done()
                    continue

                # Parse and add new links
                new_urls = parse_links(lock, response.content, current_url)
                with lock:
                    for new_url in new_urls:
                        if new_url not in visited_urls and crawl_count[0] < crawl_limit:
                            queue.put(new_url)

            except requests.RequestException as e:
                print(f"failed to retrieve {current_url}: {e}")
            finally:
                queue.task_done()

        except Exception as e:
            print(f"Unexpected error processing {current_url}: {e}")
            queue.task_done()


def parse_links(lock, content, base_url):
    soup = BeautifulSoup(content, "html.parser")
    links = set()
    for tag in soup.find_all("a", href=True):
        href = tag.get("href")
        if href.startswith("http://") or href.startswith("https://"):
            links.add(href)
        elif href.startswith("/"):
            parsed_base = urlparse(base_url)
            full_url = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            links.add(full_url)

    # Update popularity scores for all found links
    with lock:
        for link in links:
            popular_urls[link] = popular_urls.get(link, 0) + 1

    return links


def Foogle_bot():
    global popular_urls, starting_Urls

    urls_to_crawl = Queue()
    for seed_url in starting_Urls:
        urls_to_crawl.put(seed_url)

    visited_urls = set()
    crawl_limit = 100
    crawl_count = [0]
    lock = threading.Lock()
    stop_event = threading.Event()

    # Start workers
    num_workers = 50
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [
            executor.submit(
                crawl,
                urls_to_crawl,
                visited_urls,
                crawl_count,
                crawl_limit,
                lock,
                stop_event,
            )
            for _ in range(num_workers)
        ]

        # Wait for completion or limit reached
        try:
            while not stop_event.is_set() and crawl_count[0] < crawl_limit:
                time.sleep(0.1)
        except KeyboardInterrupt:
            stop_event.set()
            print("\nReceived interrupt, shutting down...")

        # Cancel any remaining tasks
        for future in futures:
            future.cancel()

        # Clear queue to help workers exit
        while not urls_to_crawl.empty():
            urls_to_crawl.get()
            urls_to_crawl.task_done()

    print(f"Total links crawled: {crawl_count[0]}")



Foogle_bot()
