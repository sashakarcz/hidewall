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

PORT = int(os.environ.get("PORT", 80))

HOST = '0.0.0.0'
TEMPLATE = 'index.html'
JAVASCRIPT = 'service-worker.js'
STATICURLPATH = '/static'
APPROUTE_ROOT = '/'
APPROUTE_JS = '/' + JAVASCRIPT
APPROUTE_APP = '/yeet'

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
    Download URL via requests and re-serve it using BeautifulSoup
    """

    query = request.args.get("y", "")

    if query:
        try:
            # Validate the input URL
            if not is_valid_url(query):
                return "Invalid URL provided", 400
            # Retrieve User-Agent header from the request
            user_agent = request.headers.get("User-Agent")

            # Define headers dictionary with User-Agent
            headers = {'User-Agent': user_agent}

            response = requests.get(query, headers=headers)

            # Parse the entire page content using BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Render the parsed content as a string
            rendered_content = soup.prettify()

            # Return the parsed content as a response
            return rendered_content

        except Exception as an_err:
            # Log the error for debugging purposes
            #error_message = f"Unexpected {an_err=}, {type(an_err)=}"
            #return error_message, 500
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

if __name__ == "__main__":
    print(f"Starting server on {HOST}:{PORT}")
    bjoern.run(app, HOST, int(PORT))
