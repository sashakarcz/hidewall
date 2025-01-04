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
from urllib.parse import quote_plus, urljoin
import gzip
import brotli

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor

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
GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
SOLARIS = "Mozilla/3.0 (SunOS 5.6 sun4m; U)"

# Read the list of blocked sites from the file
with open('blocked_sites.txt', 'r') as file:
    blocked_sites = [line.strip() for line in file]

logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_url_path=STATICURLPATH)

# Initialize Flask app
app = Flask(__name__)

# Optional OpenTelemetry instrumentation
if os.environ.get("ENABLE_OTEL", "").lower() == "true":
    # Setup OpenTelemetry tracing
    resource = Resource(attributes={
        "service.name": "hidewall-flask-app"
    })
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    span_processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)

    # Instrument Flask
    FlaskInstrumentor().instrument_app(app)

@app.route('/')
def index():
    """Display the homepage from template."""
    return render_template('index.html')

@app.route('/service-worker.js')
def service_worker():
    """Serve the service worker JS."""
    return send_from_directory('.', 'service-worker.js')

@app.route('/yeet')
def search():
    """Process the search and handle paywall bypass."""
    query = request.args.get("y", "")
    if query:
        try:
            if not is_valid_url(query):
                return "Invalid URL provided", 400
            query = query.split('?')[0]

            if any(site in query for site in blocked_sites):
                user_agent = "Mozilla/3.0 (SunOS 5.6 sun4m; U)"
            else:
                user_agent = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"

            return request_url(query, user_agent)

        except requests.exceptions.RequestException as an_err:
            logging.error("An error occurred: %s", str(an_err))
            return "An error occurred", 500

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

    # This gets rid of embedded videos
    for aside in soup.find_all('aside'):
        aside.decompose()

def handle_slideshows(soup, base_url):
    """
    Process slideshow links to ensure they have the full URL.
    """
    for a in soup.find_all('a', href=True):
        if a['href'].startswith('/picture-gallery'):
            a['href'] = urljoin(base_url, a['href'])

def request_url(url, useragent):
    """
    Download URL via requests and serve it using BeautifulSoup
    """
    # Define headers to mimic other browsers/bots
    headers = {
        'User-Agent': useragent,
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

if __name__ == "__main__":
    print(f"Starting server on {HOST}:{PORT}")
    bjoern.run(app, HOST, int(PORT))
