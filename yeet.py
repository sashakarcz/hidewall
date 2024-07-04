"""
Hidewall is a Python Flask app that uses requests and BeautifulSoup
to access content that is blocked behind a soft paywall.
"""

import logging
import os
import re
import requests
import bjoern
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, send_from_directory
from urllib.parse import quote_plus
from pynord import PyNord
import gzip
import brotli

PORT = int(os.environ.get("PORT", 80))

HOST = '0.0.0.0'
TEMPLATE = 'index.html'
JAVASCRIPT = 'service-worker.js'
CACHE_GOOGLE = 'http://webcache.googleusercontent.com/search?q=cache:'
CACHE_ARCHIVEORG = 'https://web.archive.org/web/'
CACHE_ARCHIVE = 'https://archive.today/latest/'
STATICURLPATH = '/static'
APPROUTE_ROOT = '/'
APPROUTE_JS = '/' + JAVASCRIPT
APPROUTE_APP = '/yeet'

# Read the list of blocked sites from the file
with open('blocked_sites.txt', 'r') as file:
    blocked_sites = [line.strip() for line in file]

logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_url_path=STATICURLPATH)

# Initialize NordVPN
nordvpn = PyNord()

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

            query = query.split('?')[0]

            # Connect to NordVPN if USEVPN is set to true
            if os.environ.get("USEVPN", "").lower() == "true":
                nordvpn.connect()

            rendered_content = request_url(query)  # Capture the result
            if any(site in query for site in blocked_sites):
                rendered_content = use_cache(query)  # Capture the result

            return rendered_content  # Return the result

        except requests.exceptions.RequestException as an_err:
            # Log the error for debugging purposes
            logging.error("An error occurred: %s", str(an_err))
            return "An error occurred", 500

        finally:
            # Disconnect from NordVPN if connected
            if os.environ.get("USEVPN", "").lower() == "true":
                nordvpn.disconnect()

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
    Download URL via requests and serve it using BeautifulSoup
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

    # Decompress response content if needed
    if 'Content-Encoding' in response.headers:
        if response.headers['Content-Encoding'] == 'gzip':
            response_content = gzip.decompress(response.content)
        elif response.headers['Content-Encoding'] == 'br':
            response_content = brotli.decompress(response.content)
        else:
            response_content = response.content
    else:
        response_content = response.content

    # Parse the entire page content using BeautifulSoup
    soup = BeautifulSoup(response_content, "html.parser")

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
    try:
        # Generate the complete query URL
        base_url = CACHE_ARCHIVE
        query_url = f"{base_url}{quote_plus(url)}"
        print(f"Using {query_url} for Cache")

        # Define headers dictionary with User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }

        response = requests.get(query_url, headers=headers, timeout=60)
        response.raise_for_status()

        # Decompress response content if needed
        if 'Content-Encoding' in response.headers:
            if response.headers['Content-Encoding'] == 'gzip':
                response_content = gzip.decompress(response.content)
            elif response.headers['Content-Encoding'] == 'br':
                response_content = brotli.decompress(response.content)
            else:
                response_content = response.content
        else:
            response_content = response.content

        # Parse the entire page content using BeautifulSoup
        soup = BeautifulSoup(response_content, "html.parser")

        # Remove header elements
        selectors_to_remove = '[id*="google-cache-hdr"], [id*="wm-ipp"], [id*="HEADER"]'
        elements_to_remove = soup.select(selectors_to_remove)
        for element in elements_to_remove:
            element.extract()

        # Render the parsed content as a string
        rendered_content = soup.prettify()

        # Return the parsed content as a response
        return rendered_content

    except Exception as e:
        # Log the error for debugging purposes
        logging.error("An error occurred while fetching the content: %s", str(e))
        return "An error occurred while fetching the content", 500

if __name__ == "__main__":
    print(f"Starting server on {HOST}:{PORT}")
    bjoern.run(app, HOST, int(PORT))

