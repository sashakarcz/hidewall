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
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, send_from_directory

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

    # Retrieve User-Agent header from the request
    user_agent = request.headers.get("User-Agent")

    # Define headers dictionary with User-Agent
    headers = {'User-Agent': user_agent}

    response = requests.get(url, headers=headers, timeout=10)

    # Parse the entire page content using BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")

    # Render the parsed content as a string
    rendered_content = soup.prettify()

    # Return the parsed content as a response
    return rendered_content

def use_cache(url):
    """
    Uses a web cache to download site, then remove any headers that have been added.
    """
    # Generate the complete query URL
    base_url = CACHE_ARCHIVE
    query_url = f"{base_url}{quote_plus(url)}"

    # Retrieve User-Agent header from the request
    user_agent = request.headers.get("User-Agent")

    # Define headers dictionary with User-Agent
    headers = {
        "User-Agent": user_agent
    }

    response = requests.get(query_url, headers=headers, timeout=60)

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

if __name__ == "__main__":
    print(f"Starting server on {HOST}:{PORT}")
    bjoern.run(app, HOST, int(PORT))
