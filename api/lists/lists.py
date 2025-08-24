import json
import os


def load_lists_index(filepath="lists_index.json"):
    filepath = os.path.join(os.path.dirname(__file__), filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as data_file:
            list_data = json.load(data_file)
    except FileNotFoundError:
        print(f"❌ File not found: {filepath}")
        return {"lists": []}
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return {"lists": []}

    if isinstance(list_data, list):
        return {"lists": list_data}

    return list_data
