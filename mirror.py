import os
import subprocess
import time
import smtplib
from pathlib import Path
from dotenv import load_dotenv
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import (
    Flask,
    jsonify,
    render_template,
    render_template_string,
    url_for,
    request,
)
from jinja2 import TemplateNotFound
from api.books.reading import (
    load_books,
    get_unique_years,
    filter_books_by_year,
    generate_html_table,
    summary,
)

app = Flask(__name__, template_folder="api/templates", static_folder="api/static")

load_dotenv()

TOR_DIR = os.path.expanduser(os.getenv("TOR_DIR", "~/.tor"))
HIDDEN_SERVICE_DIR = os.path.join(TOR_DIR, "hidden_service")
LOG_FILE = os.path.join(TOR_DIR, "tor.log")
ONION_ADDRESS = None
ONION_MTIME = None
MAIL_USER = os.getenv("MAIL_USER")
MAIL_RECEIVER = os.getenv("MAIL_RECEIVER")
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
    <meta charset="utf-8" />
    <title>Homepage · Sergiy Duras</title>
    <meta name="description" content="Homepage of Sergiy Duras (Сергій Дурас), a psychologist and programmer based in Ukraine." />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/static/css/base.css" />
    <link rel="stylesheet" href="/static/css/style.css" />
    <link rel="shortcut icon" href="/static/favicon.ico" />
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" /> 
  </head>
  <body>
    <header role="banner">
      <div class="container">
        <nav role="navigation">
          <ul>
            <li>
              <a href="/">
                <strong>Sergiy Duras</strong>
              </a>
            </li>
          </ul>
          <ul>
            <li>
              <a href="/about">About</a>
            </li>
            <li>
              <a href="/now">Now</a>
            </li>
            <li>
              <a href="/contact">Contact</a>
            </li>
          </ul>
        </nav>
      </div>
    </header>
    <main role="main" class="container">  <article>
  <header>
    <h1>Hello</h1>
  </header>
  <section class="grid">
    <div>
      <p>I'm <strong>Sergiy Duras</strong>, a psychologist based in <strong>Ukraine</strong> with two decades of experience at the intersection of psychology, law, and organisational risk assessment. My professional path has recently taken a strategic turn—towards programming and human-centred technology. </p>
      <p>This site serves as both my personal contact page and a space for exploring the technical tools I'm currently learning. If you'd like to know more about my background—from corporate psychology and human risk consulting to my transition into tech—please visit the <a href="/about">/about</a> page. You’ll also find a <a href="/reading">reading list</a>, spanning from 2013 to the present, as well as a <a href="/now">/now</a> page with updates on what I’m currently focused on. </p>
      <p>If you have any questions, thoughts, or just want to say hello, feel free to <a href="/contact">get in touch</a>. </p>
    </div>
    <div>
      <figure>
        <picture>
          <source media="(max-width: 600px)" srcset="/static//img/image-small.jpg" type="image/jpeg">
          <source media="(min-width: 601px)" srcset="/static//img/image-large.jpg" type="image/jpeg">
          <img src="/static//img/image-large.jpg" alt="An illustration representing calm under pressure — 大波の下で">
        </picture>
        <figcaption>大波の下で</figcaption>
      </figure>
    </div>
  </section>
</article>  </main>
    <footer role="contentinfo" class="container">  <small> &copy; 2025 Sergiy Duras <br />
        <a href="http://r56vkbtowacs5aijj3knqjsqg6sgdq6pz3mhcof7kntbaht6f3rqeryd.onion/" class="onion-link" rel="noopener noreferrer" target="_blank">
          <span class="underline-text">Access via Tor (.onion)</span>
        </a>
      </small>  </footer>  <script src="/static/js/main.js"></script> 
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


@app.route("/about")
def about():
    try:
        return render_template("about.html")
    except TemplateNotFound:
        return render_template_string(DEFAULT_HTML)


@app.route("/reading")
def reading():
    books = load_books()
    years = get_unique_years(books)
    default_year = years[-1] if years else None
    selected_year = request.args.get("year", default_year, type=int)
    filtered_books = filter_books_by_year(books, selected_year)
    table_html = generate_html_table(filtered_books)
    summary_html = summary(filtered_books, selected_year)

    try:
        return render_template(
            "reading.html",
            years=years,
            selected_year=selected_year,
            summary_html=summary_html,
            table_html=table_html,
        )
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
    msg["Subject"] = "🧅 New message"

    body = f"""
    New message from Tor website:
    Sender: {name}
    Email: {email}
    Message: {message}
    """
    msg.attach(MIMEText(body, "plain", _charset="utf-8"))

    try:
        with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USER, MAIL_PASSWORD)
            server.sendmail(MAIL_USER, MAIL_RECEIVER, msg.as_string())
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
