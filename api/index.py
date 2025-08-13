import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from api.books.reading import *

from flask import (
    Flask,
    jsonify,
    render_template,
    render_template_string,
    request,
    url_for,
)
from jinja2 import TemplateNotFound
from api.data.reading import load_books, get_unique_years, filter_books_by_year, generate_html_table, summary

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

MAIL_USER = os.getenv("MAIL_USER")
MAIL_RECEIVER = os.getenv("MAIL_RECEIVER")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_HOST = os.getenv("MAIL_HOST")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))

DEFAULT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <meta name="description" content="{{ description }}">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
<header id="header" class="container">
    <h1>Homepage</h1>
</header>
<main id="main" class="container">
    <span>🖖🏻 Hello</span>
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
        return render_template("home.html")
    except TemplateNotFound:
        return render_template_string(DEFAULT_HTML)


@app.route("/now")
def now():
    try:
        return render_template("now.html")
    except TemplateNotFound:
        return render_template_string(DEFAULT_HTML)


# Assume these functions are defined elsewhere in your application
# def load_books(): ...
# def get_unique_years(books): ...
# def filter_books_by_year(books, year): ...
# def generate_html_table(books): ...
# def summary(books, year): ...
# DEFAULT_HTML = "..."

@app.route("/reading")
def reading():
    # 1. Load data and get available years
    books = load_books()
    years = get_unique_years(books)

    # 2. Determine the default year
    # This checks if the 'years' list is not empty.
    # If it is, 'default_year' will be None.
    default_year = years[-1] if years else None

    # 3. Get the selected year from the request
    # Use 'type=int' to ensure the year is an integer.
    # The default value is set to the most recent year.
    selected_year = request.args.get("year", default_year, type=int)

    # 4. Filter books and generate content
    filtered_books = filter_books_by_year(books, selected_year)
    table_html = generate_html_table(filtered_books)
    summary_html = summary(filtered_books, selected_year)

    # 5. Render the template
    try:
        return render_template(
            "reading.html",
            years=years,
            selected_year=selected_year,
            summary_html=summary_html,
            table_html=table_html
        )
    except TemplateNotFound:
        # Fallback for when the template file is not found
        return render_template_string(DEFAULT_HTML)

@app.route("/contact")
def contact():
    try:
        return render_template("contact.html")
    except TemplateNotFound:
        return render_template_string(DEFAULT_HTML)


@app.route("/send_email", methods=["POST"])
def send_email():
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    if not all([name, email, message]):
        return jsonify({"error": "🔔 All fields are required"}), 400

    msg = MIMEMultipart()
    msg["From"] = MAIL_USER
    msg["To"] = MAIL_USER
    msg["Subject"] = "📩 New message"

    body = f"""
    New message from website:
    Sender: {name}
    Email: {email}
    Message: {message}
    """
    msg.attach(MIMEText(body, "plain", _charset="utf-8"))

    try:
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_USER, MAIL_USER, msg.as_string())
            server.quit()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "POST")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    return response


if __name__ == "__main__":
    app.run(debug=True)
