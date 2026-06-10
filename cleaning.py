import copy
import json


# Outlier thresholds — centralized for easy tuning and testability
PRICE_MIN = 0          # Sanity floor: reject negative prices
PRICE_MAX = 5000       # Outlier ceiling: reject suspicious high prices
MISSING_CATEGORY_VALUES = ("", None)  # Categories considered "garbage"


def mask_email(email):
    """
    Mask the email by keeping the first character of the local part
    and inserting '***' before the '@' and domain.

    Examples:
        "vana@gmail.com"      -> "v***@gmail.com"
        "bt@vinuni.edu.vn"    -> "b***@vinuni.edu.vn"
        "secret@xyz.com"      -> "s***@xyz.com"
        "no-at-sign"          -> "no-at-sign"  (unchanged: not a valid email)
        ""                    -> ""            (unchanged: nothing to mask)
    """
    if not email or not isinstance(email, str) or "@" not in email:
        return email

    local, _, domain = email.partition("@")
    if not local:
        return email
    return f"{local[0]}***@{domain}"


def is_valid_price(price):
    """A price is valid if it is a real number within [PRICE_MIN, PRICE_MAX]."""
    return isinstance(price, (int, float)) and not isinstance(price, bool) \
        and PRICE_MIN <= price <= PRICE_MAX


def sanitize_record(item):
    """
    Build a sanitized copy of a record:
        - drop the 'name' field
        - mask the 'email' field
    Returns a new dict; never mutates the input.
    """
    sanitized = copy.deepcopy(item)
    sanitized.pop("name", None)
    if "email" in sanitized:
        sanitized["email"] = mask_email(sanitized["email"])
    return sanitized


def clean_data(input_file, output_file):
    """Sanitize toxic data and write the cleaned result to output_file."""
    # Load the toxic data
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {input_file} not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {input_file}.")
        return
    except OSError as e:
        print(f"Error: Failed to read {input_file}: {e}")
        return

    if not isinstance(data, list):
        print(f"Error: Expected a JSON array in {input_file}.")
        return

    seen_ids = set()
    sanitized_data = []

    for item in data:
        if not isinstance(item, dict):
            continue  # skip non-object entries

        # 1. Deduplication: keep first occurrence of each id
        item_id = item.get("id")
        if item_id is None or item_id in seen_ids:
            continue

        # 2 & 3. Price sanity + outlier check (combined for clarity)
        if not is_valid_price(item.get("price")):
            continue

        # 4. Category sanity: drop records with missing/empty category
        if item.get("category") in MISSING_CATEGORY_VALUES:
            continue

        # 5. PII: drop name, mask email
        sanitized_data.append(sanitize_record(item))
        seen_ids.add(item_id)

    # Stable order: sort by id for deterministic, test-friendly output
    sanitized_data.sort(key=lambda r: r.get("id", ""))

    # Save the sanitized data
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(sanitized_data, f, indent=4, ensure_ascii=False)
    except OSError as e:
        print(f"Error: Failed to write {output_file}: {e}")
        return

    print(f"Successfully sanitized data. Output saved to {output_file}")
    print(f"Original records: {len(data)}")
    print(f"Sanitized records: {len(sanitized_data)}")


if __name__ == "__main__":
    INPUT_PATH = "toxic_sample.json"
    OUTPUT_PATH = "sanitized_sample.json"
    clean_data(INPUT_PATH, OUTPUT_PATH)
