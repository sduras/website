import asyncio
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
from flask import (Flask, abort, jsonify, render_template,
                   render_template_string, request, url_for)
from jinja2 import TemplateNotFound

from api.books.reading import (filter_books_by_year, generate_html_table,
                               get_unique_years, load_books, summary)
from api.lists.lists import load_lists_index
from api.scrap.scraping import format_output, get_updates

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
    <main role="main" class="container">
      <article>
        <h1>Hello</h1>
        <p>I'm <strong>Sergiy Duras</strong>, a psychologist based in <strong>Ukraine</strong>. </p>
        <p>Thanks for taking the time to visit my website.</p>
      </article>
    </main>
    <footer role="contentinfo" class="container">
      <small> &copy; 2025 Sergiy Duras <br />
        <a href="http://r56vkbtowacs5aijj3knqjsqg6sgdq6pz3mhcof7kntbaht6f3rqeryd.onion/" class="onion-link" rel="noopener noreferrer" target="_blank">
          <span class="underline-text">Access via Tor (.onion)</span>
        </a>
      </small>
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


@app.route("/updates")
def get_scraped_updates():
    news = asyncio.run(get_updates())
    return jsonify(news)


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
