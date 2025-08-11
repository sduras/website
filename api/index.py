import os
import smtplib
from flask import (Flask, jsonify, render_template, render_template_string,
                   url_for, request)
from jinja2 import TemplateNotFound
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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

