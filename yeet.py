"""
Hidewall is a Python Flask application designed to bypass soft paywalls on websites.
It leverages the `requests` library to fetch web content and `BeautifulSoup` to parse
and modify HTML, effectively making paywalled content accessible.

The application dynamically adjusts its User-Agent header based on whether the
requested site is identified as a 'blocked site' (i.e., known to have a paywall).
For blocked sites, it mimics Googlebot to potentially access content that would
otherwise be restricted.

Optional OpenTelemetry tracing can be enabled via environment variables for
monitoring and observability.
"""

import logging
import os
import re
import gzip
import brotli
from urllib.parse import urljoin

import requests
import bjoern
from bs4 import BeautifulSoup
from flask import Flask, request, render_template, send_from_directory

# --- OpenTelemetry Imports ---
# These imports are now at the top-level.
# They will always be attempted when the script starts.
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
# --- End OpenTelemetry Imports ---

# --- Configuration ---
# Standard port for web applications, configurable via environment variable.
PORT = int(os.environ.get("PORT", 80))
HOST = '0.0.0.0'  # Binds to all available network interfaces.

# Template and static file names.
TEMPLATE_INDEX = 'index.html'
JAVASCRIPT_SERVICE_WORKER = 'service-worker.js'

# URL paths for Flask routes.
STATIC_URL_PATH = '/static'
APP_ROUTE_ROOT = '/'
APP_ROUTE_JS = '/' + JAVASCRIPT_SERVICE_WORKER
APP_ROUTE_BYPASS = '/yeet'  # Route for paywall bypass requests.

# User-Agent strings used for web requests.
USER_AGENT_GOOGLEBOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
# A more modern generic user agent might be preferable for general Browse.
USER_AGENT_GENERIC = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"

# Read the list of blocked sites from a file.
# Each line in 'blocked_sites.txt' should contain a part of a URL
# that indicates a site known to have a paywall.
try:
    with open('blocked_sites.txt', 'r', encoding='utf-8') as file:
        BLOCKED_SITES = [line.strip() for line in file if line.strip()]
except FileNotFoundError:
    logging.warning("blocked_sites.txt not found. No sites will be specifically treated as blocked.")
    BLOCKED_SITES = []
except IOError as e:
    logging.error(f"Error reading blocked_sites.txt: {e}")
    BLOCKED_SITES = []

# --- Flask App Initialization ---
logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_url_path=STATIC_URL_PATH)

# Optional OpenTelemetry instrumentation setup.
# Only the *setup and instrumentation logic* is conditional now.
if os.environ.get("ENABLE_OTEL", "").lower() == "true":
    logging.info("OpenTelemetry ENABLE_OTEL environment variable is true. Attempting to set up tracing.")
    try:
        resource = Resource(attributes={
            "service.name": "hidewall-flask-app"
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter()
        span_processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(span_processor)
        trace.set_tracer_provider(provider)
        FlaskInstrumentor().instrument_app(app)
        logging.info("OpenTelemetry tracing enabled successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize OpenTelemetry tracing: {e}", exc_info=True)
        logging.warning("OpenTelemetry tracing will be disabled due to initialization error.")
else:
    logging.info("OpenTelemetry ENABLE_OTEL environment variable is not set to 'true'. Tracing is disabled.")


# --- Helper Functions ---

def is_valid_url(url: str) -> bool:
    """
    Validates if a given string is a well-formed HTTP or HTTPS URL.

    Args:
        url (str): The URL string to validate.

    Returns:
        bool: True if the URL is valid, False otherwise.
    """
    # Regex pattern for basic URL validation, ensuring it starts with http or https.
    pattern = re.compile(
        r'^(https?://)'  # http:// or https://
        r'([a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+\.[a-zA-Z]{2,}'  # domain, e.g., example.com
        r'(:\d+)?'  # optional port
        r'(/[-a-zA-Z0-9+&@#/%=~_|!:,.;]*)*'  # path
        r'(\?[a-zA-Z0-9+&@#/%=~_|!:,.;]*)?'  # optional query string
        r'(#[a-zA-Z0-9+&@#/%=~_|!:,.;]*)?$'  # optional fragment
    )
    return bool(pattern.match(url))


def decompress_content(response: requests.Response) -> bytes:
    """
    Decompresses the content of a requests.Response object if it is compressed
    with gzip or brotli.

    Args:
        response (requests.Response): The response object from a web request.

    Returns:
        bytes: The decompressed content, or the original content if no
               compression was detected or decompression failed.
    """
    content_encoding = response.headers.get('Content-Encoding')
    if content_encoding == 'gzip':
        try:
            return gzip.decompress(response.content)
        except Exception as e:
            logging.error(f"Gzip decompression failed: {e}")
    elif content_encoding == 'br':
        try:
            return brotli.decompress(response.content)
        except Exception as e:
            logging.error(f"Brotli decompression failed: {e}")
    return response.content


def process_html_content(soup: BeautifulSoup, base_url: str):
    """
    Processes the BeautifulSoup object to clean up HTML content,
    specifically by:
    - Correcting relative image `src` and `srcset` attributes to absolute URLs.
    - Handling `data-gl-src` and `data-gl-srcset` attributes (specific to some sites like Des Moines Register).
    - Extracting and setting `src` for images within `<figure>` tags that use `srcset` in `<source>` (e.g., NYTimes).
    - Removing all `<script>` tags to prevent paywall re-activation or analytics.
    - Removing all `<aside>` elements, which often contain embedded videos or advertisements.
    - Converting relative slideshow links to absolute URLs.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object containing the parsed HTML.
        base_url (str): The base URL of the fetched page, used for resolving
                        relative URLs.
    """
    # Fix image sources (e.g., for desmoinesregister.com, general relative paths)
    for img in soup.find_all('img'):
        if 'data-gl-src' in img.attrs:
            img['src'] = urljoin(base_url, img['data-gl-src'])
            del img['data-gl-src']
        if 'data-gl-srcset' in img.attrs:
            img['srcset'] = urljoin(base_url, img['data-gl-srcset'])
            del img['data-gl-srcset']
        elif 'src' in img.attrs and not img['src'].startswith('http'):
            img['src'] = urljoin(base_url, img['src'])
        if 'srcset' in img.attrs and not img['srcset'].startswith('http'):
            # This handles cases where srcset contains multiple URLs;
            # we try to ensure all are absolute, though typically the browser handles this.
            # For simplicity, we just make the whole attribute absolute here.
            img['srcset'] = urljoin(base_url, img['srcset'])

    # Attempt to handle srcset for figures (e.g., for nytimes)
    for figure in soup.find_all('figure'):
        srcset_img = None
        for source in figure.find_all('source'):
            if 'srcset' in source.attrs:
                # Get the first URL in srcset (assuming it's the most relevant)
                srcset_candidates = source['srcset'].split(',')
                if srcset_candidates:
                    srcset_img = srcset_candidates[0].strip().split()[0]
                break
        if srcset_img:
            img_tag = figure.find('img')
            if img_tag:
                img_tag['src'] = urljoin(base_url, srcset_img)  # Ensure absolute URL
            else:
                new_img_tag = soup.new_tag('img', src=urljoin(base_url, srcset_img))
                figure.append(new_img_tag)

    # Remove script tags to prevent paywall re-activation, tracking, or unexpected behavior.
    for script in soup.find_all('script'):
        script.extract()

    # Remove aside elements (often contains embedded videos, ads, or supplementary content).
    for aside in soup.find_all('aside'):
        aside.decompose()

    # Ensure slideshow links (e.g., for some news sites) are absolute.
    for anchor in soup.find_all('a', href=True):
        if anchor['href'].startswith('/picture-gallery'):
            anchor['href'] = urljoin(base_url, anchor['href'])


def fetch_and_process_url(url: str, user_agent: str) -> str:
    """
    Fetches content from the given URL using the specified User-Agent,
    decompresses it, parses with BeautifulSoup, and processes the HTML
    to bypass paywalls and clean up content.

    Args:
        url (str): The URL to fetch.
        user_agent (str): The User-Agent string to use for the request.

    Returns:
        str: The processed HTML content as a string.

    Raises:
        requests.exceptions.RequestException: If there's an issue with the HTTP request.
        Exception: For other unexpected errors during processing.
    """
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',  # Request compressed content
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',  # Request HTTPS if possible
        'Cache-Control': 'max-age=0',
    }

    # Fetch the content with a timeout to prevent hanging.
    response = requests.get(url, headers=headers, timeout=10)
    # Raise an HTTPError for bad responses (4xx or 5xx status codes).
    response.raise_for_status()

    # Decompress content if encoded.
    decompressed_content = decompress_content(response)

    # Parse the content using BeautifulSoup.
    soup = BeautifulSoup(decompressed_content, "html.parser")

    # Apply HTML processing rules.
    process_html_content(soup, url)

    # Return the modified HTML as a prettified string.
    return soup.prettify()


# --- Flask Routes ---

@app.route(APP_ROUTE_ROOT)
def index():
    """
    Renders the main index page of the application.

    Returns:
        str: The rendered HTML of the index template.
    """
    return render_template(TEMPLATE_INDEX)


@app.route(APP_ROUTE_JS)
def service_worker():
    """
    Serves the service worker JavaScript file. This file is typically used
    for progressive web app (PWA) features like offline capabilities or caching.

    Returns:
        flask.Response: The service worker file from the current directory.
    """
    return send_from_directory('.', JAVASCRIPT_SERVICE_WORKER)


@app.route(APP_ROUTE_BYPASS)
def bypass_paywall():
    """
    Handles requests to bypass paywalls. It expects a 'y' query parameter
    containing the URL to process.

    The function validates the URL, determines the appropriate User-Agent
    (Googlebot for blocked sites, generic for others), fetches and processes
    the content, and returns the modified HTML.

    Returns:
        Union[str, Tuple[str, int]]: The processed HTML content as a string,
                                     or an error message with an HTTP status code
                                     if validation or processing fails.
    """
    query_url = request.args.get("y", "").strip()

    if not query_url:
        logging.warning("Bypass request received with no URL provided.")
        return "Error: No URL provided.", 400

    if not is_valid_url(query_url):
        logging.warning(f"Bypass request received with invalid URL: {query_url}")
        return "Error: Invalid URL format. Please provide a valid HTTP or HTTPS URL.", 400

    # Remove query parameters from the URL before checking against blocked sites
    # to ensure consistency with entries in 'blocked_sites.txt'.
    clean_url = query_url.split('?')[0].split('#')[0]

    user_agent = USER_AGENT_GENERIC
    if any(site in clean_url for site in BLOCKED_SITES):
        user_agent = USER_AGENT_GOOGLEBOT
        logging.info(f"Using Googlebot user agent for blocked site: {clean_url}")
    else:
        logging.info(f"Using generic user agent for: {clean_url}")

    try:
        rendered_content = fetch_and_process_url(clean_url, user_agent)
        return rendered_content
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else 500
        logging.error(
            f"HTTP error {status_code} occurred while fetching '{clean_url}': {e}"
        )
        return (
            f"Error: Could not retrieve content from '{clean_url}'. "
            f"The remote server responded with status {status_code}. "
            "Please check the URL or try again later."
        ), status_code
    except requests.exceptions.ConnectionError as e:
        logging.error(f"Connection error while fetching '{clean_url}': {e}")
        return (
            f"Error: Could not connect to '{clean_url}'. "
            "Please check your internet connection or the URL."
        ), 503
    except requests.exceptions.Timeout as e:
        logging.error(f"Timeout while fetching '{clean_url}': {e}")
        return (
            f"Error: Request to '{clean_url}' timed out. "
            "The server took too long to respond."
        ), 504
    except requests.exceptions.RequestException as e:
        logging.error(f"An unknown request error occurred for '{clean_url}': {e}")
        return (
            f"Error: An unexpected network issue occurred while trying to access '{clean_url}'. "
            "Please try again."
        ), 500
    except Exception as e:
        logging.critical(
            f"An unhandled critical error occurred during URL processing for '{clean_url}': {e}",
            exc_info=True  # Log traceback for unexpected errors
        )
        return "An unexpected server error occurred.", 500


# --- Server Start ---
if __name__ == "__main__":
    logging.info(f"Starting Hidewall server on {HOST}:{PORT}")
    try:
        # Bjoern is a fast, lightweight WSGI server.
        bjoern.run(app, HOST, int(PORT))
    except Exception as e:
        logging.critical(f"Failed to start Bjoern server: {e}")
        # Exit with a non-zero status code to indicate failure.
        import sys
        sys.exit(1)
