import bjoern
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from flask import Flask, request, render_template_string

app = Flask(__name__, static_url_path='/static')

# HTML template for the homepage
home_template = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Hidewalls</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<link rel="stylesheet" href="static/fonts/material-design-iconic-font/css/material-design-iconic-font.min.css">

<link rel="stylesheet" href="static/css/style.css">
<meta name="robots" content="noindex, follow">
</head>
<body>
  <div class="wrapper">
    <div class="inner">
      <form method="GET" action="/yeet">
      <h3>Be Gone Paywalls!</h3>
      <p>Paste the URL to the site you wish to visit in the box, and then click Remove Paywalls.</p>
      <label class="form-group">
        <input type="text" name="y" class="form-control" required>
        <span>http://news.site/blocked</span>
        <span class="border"></span>
      </label>
      <button>Remove Paywalls</button>
     </form>
    </div>
  </div>
      {% if results %}
    <ul>
        {% for result in results %}
        <li><a href="{{ result['link'] }}">{{ result['title'] }}</a></li>
        {% endfor %}
    </ul>
    {% endif %}
 </body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(home_template)

@app.route("/yeet")
def search():
    query = request.args.get("y", "")
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

