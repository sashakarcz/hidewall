"""
Hidewall is a Python Flask app that uses the Google Web Cache, or
Wayback Machine to access content that is blocked behind a soft paywall.
"""

import logging
import os
from urllib.parse import quote_plus
import requests
import re
import bjoern
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, send_from_directory

PORT = int(os.environ.get("PORT", 80))

HOST = '0.0.0.0'
TEMPLATE = 'index.html'
JAVASCRIPT = 'service-worker.js'
STATICURLPATH = '/static'
CACHE_GOOGLE = 'http://webcache.googleusercontent.com/search?q=cache:'
CACHE_ARCHIVEORG = 'https://web.archive.org/web/'
CACHE_ARCHIVE = 'https://archive.is/latest/'
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
    Present the JS for browser
    """
    return send_from_directory('.', JAVASCRIPT)

@app.route(APPROUTE_APP)
def search():
    """
    Lookup a source from various caches
    """

    query = request.args.get("y", "")
    # url_query = request.args.get("url_query", "")

    if query:
        try:
            base_url = CACHE_GOOGLE
            if any(site in query for site in blocked_sites): 
              base_url = CACHE_ARCHIVEORG
            if "wsj.com" in query:
              base_url = CACHE_ARCHIVE
              query = re.sub(r"\?.*", "", query)

            # Generate the complete query URL
            query_url = f"{base_url}{quote_plus(query)}"

            # Retrieve User-Agent header from the request
            #user_agent = request.headers.get("User-Agent")

            # Define headers dictionary with User-Agent
            #headers = {
            #    "User-Agent": user_agent
            #}
            headers = {
              "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36" ,
              'referer':'https://www.google.com/'
            }
            response = requests.get(query_url, headers=headers)

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

        except Exception as an_err:
            error_message = f"Unexpected {an_err=}, {type(an_err)=}"
            return error_message, 500

    # Handle the case where query is empty
    return "No query provided", 400

if __name__ == "__main__":
    print(f"Starting server on {HOST}:{PORT}")
    bjoern.run(app, HOST, PORT)
