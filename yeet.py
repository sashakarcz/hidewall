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
from flask import Flask, request, render_template, send_from_directory, redirect, url_for
from urllib.parse import quote_plus, urljoin
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

            if any(site in query for site in blocked_sites):
                return use_cache_iframe(query)

            rendered_content = request_url(query)  # Capture the result
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

def decompress_content(response):
    """
    Decompress response content if needed.
    """
    try:
        if 'Content-Encoding' in response.headers:
            if response.headers['Content-Encoding'] == 'gzip':
                return gzip.decompress(response.content)
            elif response.headers['Content-Encoding'] == 'br':
                return brotli.decompress(response.content)
    except Exception as e:
        logging.error("Decompression failed: %s", str(e))
    
    # Fall back to original content if decompression fails
    return response.content

def handle_images_and_asides(soup, base_url):
    """
    Process images and remove aside elements in the BeautifulSoup object.
    """

    # This is logic to get desmoinesregister.com working
    for img in soup.find_all('img'):
        if 'data-gl-src' in img.attrs:
            img['src'] = urljoin(base_url, img['data-gl-src'])
            del img['data-gl-src']
        if 'data-gl-srcset' in img.attrs:
            img['srcset'] = urljoin(base_url, img['data-gl-srcset'])
            del img['data-gl-srcset']
        elif 'src' in img.attrs:
            img['src'] = urljoin(base_url, img['src']) if not img['src'].startswith('http') else img['src']
        if 'srcset' in img.attrs and not img['srcset'].startswith('http'):
            img['srcset'] = urljoin(base_url, img['srcset'])

    # This is an attempt to build out similar logic for nytimes
    for figure in soup.find_all('figure'):
        srcset_img = None
        for source in figure.find_all('source'):
            if 'srcset' in source.attrs:
                srcset_img = source['srcset'].split(",")[0].split()[0]  # Get the first URL in srcset
                break
        if srcset_img:
            img_tag = figure.find('img')
            if img_tag:
                img_tag['src'] = srcset_img
            else:
                img_tag = soup.new_tag('img', src=srcset_img)
                figure.append(img_tag)

    # This gets rid of embeded videos
    for aside in soup.find_all('aside'):
        aside.decompose()

def handle_slideshows(soup, base_url):
    """
    Process slideshow links to ensure they have the full URL.
    """
    for a in soup.find_all('a', href=True):
        if a['href'].startswith('/picture-gallery'):
            a['href'] = urljoin(base_url, a['href'])

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

    # Decompress response content
    response_content = decompress_content(response)

    # Parse the entire page content using BeautifulSoup
    soup = BeautifulSoup(response_content, "html.parser")

    # Remove all <script> tags and their contents
    for script in soup.find_all('script'):
        script.extract()

    # Handle images, aside elements, and slideshows
    handle_images_and_asides(soup, url)
    handle_slideshows(soup, url)

    # Render the parsed content as a string
    rendered_content = soup.prettify()

    # Return the parsed content as a response
    return rendered_content

def use_cache_iframe(url):
    """
    Uses an iframe to display web archive content.
    """
    base_url = CACHE_ARCHIVE
    query_url = f"{base_url}{quote_plus(url)}"
    iframe_html = f'<iframe src="{query_url}" width="100%" height="1000px"></iframe>'
    return iframe_html

if __name__ == "__main__":
    print(f"Starting server on {HOST}:{PORT}")
    bjoern.run(app, HOST, int(PORT))
