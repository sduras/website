import datetime
import gzip
import json
import os
import shutil

DATAFILE = "lists_index.json"
BACKUP_DIR = os.path.dirname(__file__)


def backup_json_file(filepath):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    backup_filename = f"{os.path.splitext(filepath)[0]}_{timestamp}.json.gz"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    with open(filepath, "rb") as f_in:
        with gzip.open(backup_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

    print(f"✅ Backup created: {backup_filename}")


def load_data(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌  Error loading {filepath}: {e}")
        return {"lists": []}


def save_data(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅  Updated file saved: {filepath}")


def list_topics(data):
    tags = set()
    for lst in data["lists"]:
        tags.update(lst.get("tags", []))
    return sorted(tags)


def add_new_list(data):
    print("\n➡  Adding new list")

    title = input("Title: ").strip()
    print("Select list type:")
    print("1. Ordered (numbered list)")
    print("2. Unordered (bullet list)")
    type_choice = input("Enter 1 or 2: ").strip()

    if type_choice == "1":
        list_type = "ordered"
    elif type_choice == "2":
        list_type = "unordered"
    else:
        print("⚠️ Invalid choice, defaulting to 'unordered'")
        list_type = "unordered"

    tags = input("Tags (comma-separated): ").strip().split(",")

    items = []
    print("Now enter list items (type 'done' to finish):")

    while True:
        text = input("Item text: ").strip()
        if text.lower() == "done":
            break
        note = input("Note (optional): ").strip() or None

        raw_link = input("Link (optional): ").strip()
        if raw_link == "":
            link = None
        elif raw_link.startswith(("http://", "https://")):
            link = raw_link
        else:
            link = "https://" + raw_link

        items.append({"text": text, "note": note, "link": link})

    new_list = {
        "title": title,
        "type": list_type if list_type in ("ordered", "unordered") else "unordered",
        "tags": [tag.strip() for tag in tags if tag.strip()],
        "items": items,
    }

    data["lists"].append(new_list)
    print(f"✅  Added list: {title}")


def main():
    filepath = os.path.join(BACKUP_DIR, DATAFILE)

    print(f"📂  Loading data from: {filepath}")
    data = load_data(filepath)

    if not data or "lists" not in data:
        print("❌  Invalid or missing list structure. Exiting.")
        return

    backup_json_file(filepath)

    print("\nAvailable operations:")
    print("1. Add new list")
    print("2. Show all topics")
    print("3. Cancel")

    choice = input("Choose an option (1/2/3): ").strip()

    if choice == "1":
        add_new_list(data)
        save_data(filepath, data)
    elif choice == "2":
        print("\nAvailable topics:")
        for t in list_topics(data):
            print(f"- {t}")
    else:
        print("❌  No changes made.")


if __name__ == "__main__":
    main()
