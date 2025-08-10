import os
import subprocess
import time

from flask import (Flask, jsonify, render_template, render_template_string,
                   url_for)
from jinja2 import TemplateNotFound

app = Flask(__name__, template_folder="templates", static_folder="static")


TOR_DIR = os.path.expanduser("~/.tor")
HIDDEN_SERVICE_DIR = os.path.join(TOR_DIR, "hidden_service")
LOG_FILE = os.path.join(TOR_DIR, "tor.log")

ONION_ADDRESS = None
ONION_MTIME = None


def install_dependencies():
    print("Installing dependencies..")
    os.system("pkg update -y && pkg upgrade -y")
    os.system("pkg install python tor -y")
    os.system("pip install --upgrade pip")
    os.system("pip install flask")


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
    <h1>{{ heading }}</h1>
</header>
<main id="main" class="container">
    <span>{{ message }}</span>
</main>
<footer id="footer" class="container">
    <p>&copy; {{ year }}</p>
</footer>
</body>
</html>
"""


@app.route("/")
def home():
    data = {
        "title": "Anonymous Website",
        "heading": "Welcome to my Tor Hidden Service",
        "message": "🖖🏻 Hello, Sergiy",
        "year": time.strftime("%Y"),
    }
    try:
        return render_template("index.html", **data)
    except TemplateNotFound:
        return render_template_string(DEFAULT_HTML, **data)


@app.route("/api/status")
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
