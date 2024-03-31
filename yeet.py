"""
Hidewall is a Python Flask app that uses requests and BeautifulSoup
to access content that is blocked behind a soft paywall.
"""

import logging
import os
import re
from urllib.parse import quote_plus  # Added import
import requests
import bjoern
import socks
import socket
from bs4 import BeautifulSoup
from flask import Flask, redirect, request, render_template, send_from_directory

PORT = int(os.environ.get("PORT", 80))

HOST = '0.0.0.0'
TEMPLATE = 'index.html'
JAVASCRIPT = 'service-worker.js'
CACHE_GOOGLE = 'http://webcache.googleusercontent.com/search?q=cache:'
CACHE_ARCHIVEORG = 'https://web.archive.org/web/'
CACHE_ARCHIVE = 'https://archive.is/latest/'
STATICURLPATH = '/static'
APPROUTE_ROOT = '/'
APPROUTE_JS = '/' + JAVASCRIPT
APPROUTE_APP = '/yeet'
PRIVACY_POLICY = '/privacy'
PRIVACY_TEMPLATE = 'privacy.html'

# Read the list of blocked sites from the file
with open('blocked_sites.txt', 'r') as file:
    blocked_sites = [line.strip() for line in file]

logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_url_path=STATICURLPATH)

@app.route(PRIVACY_POLICY)
def index():
    """
    Display the privacy policy from template
    """
    return render_template(PRIVACY_TEMPLATE)

@app.route(APPROUTE_ROOT)
def index():
    """
    Display the homepage from template
    """
    return render_template(TEMPLATE)

@app.route(APPROUTE_JS)
def service_worker():
    """
    Present the JS for the browser
    """
    return send_from_directory('.', JAVASCRIPT)

@app.route(APPROUTE_APP)
def search():
    """
    Checks the URL, then decides to use a web cache or requests to render content
    """

    query = request.args.get("y", "")

    if query:
        try:
            # Validate the input URL
            if not is_valid_url(query):
                return "Invalid URL provided", 400

            rendered_content = request_url(query)  # Capture the result
            if any(site in query for site in blocked_sites):
                rendered_content = use_cache(query)  # Capture the result

            return rendered_content  # Return the result

        except requests.exceptions.RequestException as an_err:
            # Log the error for debugging purposes
            logging.error("An error occurred: %s", str(an_err))
            return "An error occurred", 500

    # Handle the case where query is empty
    return "No query provided", 400

def is_valid_url(url):
    """
    Validate if a given URL is valid.
    """

    # Use a regex pattern for basic URL validation
    pattern = re.compile(r'^(https?://[-A-Za-z0-9+&@#/%?=~_|!:,.;]*[-A-Za-z0-9+&@#/%=~_|])')
    return bool(pattern.match(url))

def request_url(url):
    """
    Download URL via requests and servce it using BeautifulSoup
    """

    # Define headers to mimic GoogleBot
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }

    response = requests.get(url, headers=headers, timeout=10)

    # Parse the entire page content using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Remove all <script> tags and their contents
    for script in soup.find_all('script'):
        script.extract()

   # Render the parsed content as a string
    rendered_content = soup.prettify()

    # Return the parsed content as a response
    return rendered_content

def use_cache(url):
    """
    Uses a web cache to download site, then remove any headers that have been added.
    """

    USE_PROXY = os.getenv("USE_PROXY", "").lower() in ["true", "1", "yes"]

    # Create a socket object with the SOCKS5 proxy
    if USE_PROXY:
        SOCKS_PROXY = str(os.environ.get("PROXY", ""))
        PROXY_PORT = str(os.environ.get("PROXY_PORT", ""))
        USERNAME = str(os.environ.get("USERNAME", ""))
        PASSWORD = str(os.environ.get("PASSWORD", ""))

        # Check if PROXY_PORT is empty or not
        if not PROXY_PORT:
            # Set a default port if PROXY_PORT is empty
            PROXY_PORT = "1080"  # Change to your desired default port

        # Convert PROXY_PORT to integer
        try:
            PROXY_PORT = int(PROXY_PORT)
        except ValueError:
            # Handle the case where PROXY_PORT is not a valid integer
            logging.error("Invalid value for PROXY_PORT, using default port 1080")
            PROXY_PORT = 1080  # Change to your desired default port

        # Set the SOCKS5 proxy
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, SOCKS_PROXY, PROXY_PORT, True, USERNAME, PASSWORD)
        socket.socket = socks.socksocket  # Override the default socket with the SOCKS-enabled socket
    else:
        pass  # Use default socket

    # Generate the complete query URL
    base_url = CACHE_ARCHIVE
    query_url = f"{base_url}{quote_plus(url)}"
    print(f"Using {query_url} for Cache")

    # Retrieve User-Agent header from the request
    user_agent = request.headers.get("User-Agent")

    # Define headers dictionary with User-Agent
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    return redirect(query_url, code=302)

    try:
        response = requests.get(query_url, headers=headers, timeout=60)
        response.raise_for_status()

        # Log the response content for debugging
        logging.info("Response Content: %s", response.text)
    
        # Reset the socket settings to the default
        socks.setdefaultproxy()
        
        # Parse the entire page content using BeautifulSoup
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove header elements
        selectors_to_remove = '[id*="google-cache-hdr"], [id*="wm-ipp"], [id*="HEADER"]'
        elements_to_remove = soup.select(selectors_to_remove)
        for element in elements_to_remove:
            element.extract()

        # Render the parsed content as a string
        rendered_content = soup.prettify()

        # Return the parsed content as a response
        return rendered_content

    except requests.exceptions.RequestException as e:
        # Log the error for debugging purposes
        logging.error("An error occurred: %s", str(e))
        # Reset the socket settings to the default in case of error
        socks.setdefaultproxy()
        return "An error occurred while fetching the content", 500

if __name__ == "__main__":
    print(f"Starting server on {HOST}:{PORT}")
    bjoern.run(app, HOST, int(PORT))
