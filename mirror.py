import os
import smtplib
import subprocess
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    render_template,
    render_template_string,
    request,
    url_for,
)
from jinja2 import TemplateNotFound

from api.books.reading import (
    filter_books_by_year,
    generate_html_table,
    get_unique_years,
    load_books,
    summary,
)
from api.lists.lists import load_lists_index

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
    <meta name="description" content="Sergiy Duras (Сергій Дурас) is a Ukrainian psychologist and Python developer specializing in behavioral risk, human-centered design, and solution-focused brief therapy (SFBT). This personal website offers insights into his multidisciplinary work at the intersection of psychology and technology, with updates on current projects, reading lists, and contact information." />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="stylesheet" href="/static/css/base.css" />
    <link rel="stylesheet" href="/static/css/style.css" />
    <link rel="shortcut icon" href="https://sergiy.duras.org/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/static/favicon.svg" /> 
    <meta name="author" content="Sergiy Duras · Psychologist applying behavioral risk insights, SFBT principles, and Python development to build human-centered, solution-oriented software.">
    <meta name="keywords" content="Sergiy Duras, psychologist, legal expert, human risk, solution-focused therapy, SFBT, behavioral risk, Python developer, Ukraine">
    <meta name="robots" content="index, follow">
    <meta property="og:type" content="website">
    <meta property="og:title" content="Sergiy Duras">
    <meta property="og:description" content="Psychologist applying behavioral risk insights, SFBT principles, and Python development to build human-centered, solution-oriented software.">
    <meta property="og:url" content="https://sergiy.duras.org/">
    <meta property="og:image" content="https://sergiy.duras.org/static/img/npa2025-large.jpg">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="About · Sergiy Duras">
    <meta name="twitter:description" content="Psychologist applying behavioral risk insights, SFBT principles, and Python development to build human-centered, solution-oriented software.">
    <meta name="twitter:image" content="https://sergiy.duras.org/static/img/npa2025-large.jpg">
    <script type="application/ld+json">
      {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": "Sergiy Duras",
        "url": "https://sergiy.duras.org",
        "image": "https://sergiy.duras.org/static/img/npa2025-large.jpg",
        "sameAs": ["https://www.psiwell.com/", "https://www.linkedin.com/in/duras/", "https://github.com/sduras", "https://codeberg.org/duras", "https://nownownow.com/p/svyZ", "https://npa-ua.org/register/duras-serhiy-hennadiyovych-2228/", "https://vpa.org.ua/about/chleni-asotsiatsiy/povni-diysni-chleni-asotsiatsiy/"],
        "jobTitle": "Psychologist, Legal Expert, Python Developer",
        "worksFor": {
          "@type": "Organization",
          "name": "Psiwell",
          "url": "https://www.psiwell.com/"
        },
        "alumniOf": [{
          "@type": "CollegeOrUniversity",
          "name": "Kharkiv University",
          "url": "https://karazin.ua/en/"
        }],
        "knowsAbout": ["Psychology", "Law", "Behavioral Risk", "Polygraph", "Solution-Focused Brief Therapy", "Python", "Human-Centered Design"],
        "description": "Psychologist applying behavioral risk insights, SFBT principles, and Python development to build human-centered, solution-oriented software.",
        "nationality": "Ukrainian"
      }
    </script>
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
      <p>I'm <strong>Sergiy Duras</strong>, a psychologist based in <strong>Ukraine</strong> with two decades of experience at the intersection of psychology, law, and organisational risk assessment. My professional path has recently taken a strategic turn — towards programming and human-centred technology. </p>
      <p>This site serves as both my personal contact page and a space for exploring the tools I'm currently learning. If you'd like to know more about my background — from corporate psychology and human risk consulting to my transition into tech — please visit the <a href="/about">/about</a> page. You’ll also find a <a href="/reading">reading list</a>, spanning from 2013 to the present, a number of <a href="/lists">/lists</a> on different subjects, as well as a <a href="/now">/now</a> page with updates on what I’m currently focused on. </p>
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
      </small>  </footer> 
<script async src="https://www.googletagmanager.com/gtag/js?id=G-VVK7WTG3T0"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-VVK7WTG3T0');
</script> 
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
        
@app.route("/scraping")
def scraping_dashboard():
    exercises = {
        "software": {"title": "Software", "enabled": True, "fetcher": get_updates},
        "news": {"title": "News", "enabled": True, "fetcher": get_updates},
        "weather": {"title": "Weather", "enabled": False, "fetcher": None},
    }

    selected = request.args.get("exercise", "")
    articles = []

    if selected in exercises and exercises[selected]["enabled"]:
        raw_data = asyncio.run(exercises[selected]["fetcher"]())
        updates = raw_data["updates"].get(selected, {})

        for source, items in updates.items():
            for item in items:
                articles.append(
                    {
                        "source": source,
                        "title": item.get("title", ""),
                        "text": item.get("text") or item.get("description", ""),
                        "url": item.get("url", ""),
                        "fetched_at": item.get("fetched_at", ""),
                        "fetched_at_kyiv": item.get("fetched_at_kyiv", ""),
                    }
                )

        if selected == "software":
            custom_order = ["Debian", "Vim", "Python", "GnuPG", "aShell", "cmus"]
            order_index = {name.lower(): i for i, name in enumerate(custom_order)}

            articles.sort(
                key=lambda x: order_index.get(x["title"].lower(), len(custom_order))
            )

    return render_template(
        "scraping.html",
        exercises=exercises,
        selected_exercise=selected,
        articles=articles,
    )



@app.route("/lists")
def lists():
    selected_topic = request.args.get("topic")

    list_data = load_lists_index()
    all_lists = list_data.get("lists", [])

    print("🔍 Number of loaded lists:", len(all_lists))
    print("🔍 Example list:", all_lists[0] if all_lists else "None")

    topics = sorted(set(tag for lst in all_lists for tag in lst.get("tags", [])))

    if selected_topic:
        filtered_lists = [
            lst for lst in all_lists if selected_topic in lst.get("tags", [])
        ]
    else:
        filtered_lists = all_lists

    return render_template(
        "lists.html", lists=filtered_lists, topics=topics, selected_topic=selected_topic
    )


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
