import bjoern
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from flask import Flask, request, render_template_string

app = Flask(__name__, static_url_path='/static')

# HTML template for the search page
search_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Hidewalls</title>
</head>
<body>
    <h1>Paywall Bypass</h1>
    <form method="GET" action="/search">
        <input type="text" name="query" placeholder="http://news.site/blocked">
        <input type="submit" value="Remove Paywall">
    </form>
    {% if results %}
    <h2>Search Results</h2>
    <ul>
        {% for result in results %}
        <li><a href="{{ result['link'] }}">{{ result['title'] }}</a></li>
        {% endfor %}
    </ul>
    {% endif %}
<script src="/index.js"></script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(search_template)

@app.route("/search")
def search():
    query = request.args.get("query", "")
    url_query = request.args.get("url_query", "")
    
    if query:
      base_url = "http://webcache.googleusercontent.com/search?q=cache:"
      if "nytimes.com" in query:
          base_url = "https://web.archive.org/web/"

      # Generate the complete query URL
      query_url = f"{base_url}{quote_plus(query)}"
      response = requests.get(query_url)
    
      # Parse the entire page content using BeautifulSoup
      soup = BeautifulSoup(response.text, "html.parser")
      
      # Remove header elements
      selectors_to_remove = '[id*="google-cache-hdr"], [id*="wm-ipp"]'
      elements_to_remove = soup.select(selectors_to_remove)
      for element in elements_to_remove:
        element.extract()
    
      # Render the parsed content as a string
      rendered_content = soup.prettify()
    
      return render_template_string(rendered_content)

if __name__ == "__main__":
    host = '0.0.0.0'
    port = 80
    print(f"Starting server on {host}:{port}")
    bjoern.run(app, host, port)

