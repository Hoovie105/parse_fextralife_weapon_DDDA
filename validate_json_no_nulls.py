import json
import sys

def find_nulls(data, path="root"):
    """
    Recursively search for None (null) values in JSON data.
    Returns a list of paths where nulls are found.
    """
    null_paths = []

    if isinstance(data, dict):
        for key, value in data.items():
            new_path = f"{path}.{key}"
            if value is None:
                null_paths.append(new_path)
            else:
                null_paths.extend(find_nulls(value, new_path))

    elif isinstance(data, list):
        for index, item in enumerate(data):
            new_path = f"{path}[{index}]"
            if item is None:
                null_paths.append(new_path)
            else:
                null_paths.extend(find_nulls(item, new_path))

    return null_paths


def validate_json_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return False

    nulls = find_nulls(data)

    if nulls:
        print(f"❌ Validation failed — {len(nulls)} null value(s) found:\n")
        for path in nulls:
            print(f"  - {path}")
        return False

    print("✅ Validation passed — no null values found.")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_json_no_nulls.py <file.json>")
        sys.exit(1)

    file_path = sys.argv[1]
    success = validate_json_file(file_path)

    sys.exit(0 if success else 1)
