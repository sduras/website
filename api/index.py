import os
from flask import (Flask, jsonify, render_template, render_template_string,
                   url_for)
from jinja2 import TemplateNotFound

app = Flask(__name__)

DEFAULT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <meta name="description" content="{{ description }}">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
    <link rel="shortcut icon" href="/favicon.ico">
</head>
<body>
<header id="header" class="container">
    <h1>Homepage</h1>
</header>
<main id="main" class="container">
    <span>🖖🏻 Hello, Sergiy</span>
</main>
<footer id="footer" class="container">
    <p>&copy; 2025</p>
</footer>
</body>
</html>
"""


@app.route("/")
def home():
    try:
        return render_template("index.html")
    except TemplateNotFound:
        return render_template_string(DEFAULT_HTML)


if __name__ == "__main__":
    app.run(debug=True)

