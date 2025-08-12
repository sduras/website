import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import (
    Flask,
    jsonify,
    render_template,
    render_template_string,
    request,
    url_for,
)
from jinja2 import TemplateNotFound

app = Flask(__name__, template_folder="templates", static_folder="static")

MAIL_USER = os.getenv("MAIL_USER")
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


@app.route("/reading")
def reading():
    try:
        return render_template("reading.html")
    except TemplateNotFound:
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
