import json
import os
from datetime import datetime

from markupsafe import Markup


class Book:
    def __init__(self, **kwargs):
        date_str = kwargs.get("Date Read")
        if isinstance(date_str, str):
            self.date_read = datetime.strptime(date_str, "%Y-%m-%d")
        else:
            self.date_read = None

        self.author = kwargs["Author"]
        self.title = kwargs["Title"]
        self.published = kwargs["Published"]
        self.format = kwargs.get("Format", "")
        self.rating = kwargs["Rating"] if kwargs["Rating"] != "0" else ""
        self.note = kwargs.get("Note", "")
        self.note_file = kwargs.get("NoteFile", "")


def load_books(filepath="books.json"):
    filepath = os.path.join(os.path.dirname(__file__), filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            books_data = json.load(f)
            books = []
            for entry in books_data:
                try:
                    book = Book(**entry)
                    if book.date_read is not None:
                        books.append(book)
                except Exception as e:
                    print(f"Skipping book due to error: {e}\nData: {entry}")
            return books
    except FileNotFoundError:
        print(f"Error: File '{filepath}' not found.")
        return []
    except Exception as e:
        print(f"Error loading books: {e}")
        return []


def get_unique_years(books):
    return sorted({book.date_read.year for book in books})


def filter_books_by_year(books, target_year):
    return [book for book in books if book.date_read.year == target_year]


def generate_html_table(books):
    table_rows = ""
    for book in books:
        date_read = book.date_read.strftime("%Y-%m-%d")
        table_rows += f"""
            <tr>
                <td data-label="read">{date_read}</td>
                <td data-label="author">{book.author}</td>
                <td data-label="title">{book.title}</td>
                <td data-label="published">{book.published}</td>
                <td data-label="format">{book.format}</td>
                <td data-label="rating">{generate_rating_stars(book.rating)}</td>
            </tr>"""
    return table_rows


def generate_rating_stars(rating):
    try:
        rating = int(rating)
    except (ValueError, TypeError):
        return ""

    stars = "".join(
        (
            '<span class="starsf">&starf;</span>'
            if i < rating
            else '<span class="stars">&star;</span>'
        )
        for i in range(5)
    )
    return Markup(stars)


def summary(books, target_year):
    num_books = len(books)

    valid_books = [book for book in books if str(book.rating).isdigit()]
    if valid_books:
        highest_rating = max(int(book.rating) for book in valid_books)
        highest_rating_books = [
            (book.title, book.author)
            for book in valid_books
            if int(book.rating) == highest_rating
        ]
        highest_rating_info = ", ".join(
            f'<strong style="color: #BF6E00;">{title}</strong> by {author}'
            for title, author in highest_rating_books
        )
        return (
            f"Books Read in {target_year}: <strong><span class='books_in_year' style='color: darkorange'>{num_books}</span></strong><br><br>"
            
            f"Best book(s): {highest_rating_info}."
        )
    return f"No valid ratings found for year {target_year}."


if __name__ == "__main__":
    books = load_books()
    print(f"Loaded {len(books)} books.")
    for book in books:
        print(book.__dict__)
