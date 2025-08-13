import os
import subprocess
import time
import smtplib
from pathlib import Path
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import (Flask, jsonify, render_template, render_template_string,
                   url_for, request)
from jinja2 import TemplateNotFound

app = Flask(__name__, template_folder="api/templates", static_folder="api/static")

load_dotenv()

TOR_DIR = os.path.expanduser(os.getenv("TOR_DIR", "~/.tor"))
HIDDEN_SERVICE_DIR = os.path.join(TOR_DIR, "hidden_service")
LOG_FILE = os.path.join(TOR_DIR, "tor.log")
ONION_ADDRESS = None
ONION_MTIME = None
MAIL_USER = os.getenv("MAIL_USER")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_HOST = os.getenv("MAIL_HOST")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))


def install_dependencies():
    print("Installing dependencies..")
    os.system("pkg update -y && pkg upgrade -y")
    os.system("pkg install python tor -y")
    os.system("pip install --upgrade pip")
    os.system("pip install python-dotenv")
    os.system("pip install -r requirements.txt")


def configure_tor():
    print("Configuring Tor..")
    if not os.path.exists(HIDDEN_SERVICE_DIR):
        os.makedirs(HIDDEN_SERVICE_DIR, mode=0o700)

    torrc_path = os.path.join(TOR_DIR, "torrc")
    with open(torrc_path, "w") as f:
        f.write(f"HiddenServiceDir {HIDDEN_SERVICE_DIR}/\n")
        f.write("HiddenServicePort 80 127.0.0.1:5000\n")
        f.write(f"Log notice file {LOG_FILE}\n")


def start_tor():
    print("Starting Tor...")
    subprocess.Popen(
        ["tor", "-f", os.path.join(TOR_DIR, "torrc")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(15)


def load_onion_address(force_reload=False):
    global ONION_ADDRESS, ONION_MTIME

    hostname_file = os.path.join(HIDDEN_SERVICE_DIR, "hostname")
    if os.path.exists(hostname_file):
        mtime = os.path.getmtime(hostname_file)
        if force_reload or mtime != ONION_MTIME:
            with open(hostname_file, "r") as f:
                ONION_ADDRESS = f.read().strip()
            ONION_MTIME = mtime
    else:
        ONION_ADDRESS = None
        ONION_MTIME = None


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
        

@app.route("/status")
def status():
    # Check if .onion changed since last read
    load_onion_address()
    return jsonify({"status": "running", "onion": ONION_ADDRESS})


if __name__ == "__main__":
    print("Starting setup...")
    install_dependencies()
    configure_tor()
    start_tor()

    load_onion_address(force_reload=True)

    if ONION_ADDRESS:
        print(f"Your Tor hidden service is running at: {ONION_ADDRESS}")
    else:
        print("Error: .onion address not found.")

    print("Starting Flask server...")
    app.run(host="127.0.0.1", port=5000)
