import json
import argparse
import os

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def deduplicate_and_merge(files, merged_out, duplicates_out):
    datasets = [load_json(f) for f in files]
    items_list = [data["items"] for data in datasets]

    duplicates = {"format_version": "1", "items": {}}
    duplicates_exact = {}  # {(name, id): entry}
    duplicates_name = set()
    duplicates_id = set()

    # Compare across all files
    for i, items1 in enumerate(items_list):
        for j, items2 in enumerate(items_list):
            if i >= j:
                continue
            for item_type, entries in items1.items():
                for e1 in entries:
                    for e2 in items2.get(item_type, []):
                        if e1["name"] == e2["name"] and e1["custom_model_data"] == e2["custom_model_data"]:
                            duplicates_exact[(e1["name"], e1["custom_model_data"])] = e1
                        elif e1["name"] == e2["name"]:
                            duplicates_name.add(e1["name"])
                        elif e1["custom_model_data"] == e2["custom_model_data"]:
                            duplicates_id.add(e1["custom_model_data"])

    def filter_items(items, collect_duplicates=False):
        new_items = {}
        for item_type, entries in items.items():
            filtered = []
            for e in entries:
                key = (e["name"], e["custom_model_data"])
                if key in duplicates_exact:
                    if collect_duplicates:
                        duplicates["items"].setdefault(item_type, [])
                        if not any(
                            d["name"] == e["name"] and d["custom_model_data"] == e["custom_model_data"]
                            for d in duplicates["items"][item_type]
                        ):
                            duplicates["items"][item_type].append(e)
                    continue
                if e["name"] in duplicates_name:
                    continue
                if e["custom_model_data"] in duplicates_id:
                    continue
                filtered.append(e)
            if filtered:
                new_items[item_type] = filtered
        return new_items

    # Clean and save each file
    cleaned_datasets = []
    for f, data in zip(files, datasets):
        base = os.path.splitext(os.path.basename(f))[0]
        data["items"] = filter_items(data["items"])
        save_json(data, f"{base}_clean.json")
        cleaned_datasets.append(data["items"])
        print(f"✅ Cleaned {f} → {base}_clean.json")

    # Collect duplicates (only once, after filtering)
    for items in items_list:
        filter_items(items, collect_duplicates=True)

    # Merge cleaned sets
    merged = {"format_version": "1", "items": {}}
    for items in cleaned_datasets:
        for item_type, entries in items.items():
            merged["items"].setdefault(item_type, []).extend(entries)

    save_json(merged, merged_out)
    save_json(duplicates, duplicates_out)

    print(f"✅ Merged output → {merged_out}")
    print(f"✅ Unique exact duplicates saved → {duplicates_out}")
    print(f"❌ Removed same-name dif-ID: {duplicates_name}")
    print(f"❌ Removed same-ID dif-name: {duplicates_id}")
    print(f"⚠️ Moved exact duplicates (unique): {list(duplicates_exact.keys())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate and merge multiple JSON mapping files.")
    parser.add_argument("files", nargs="+", help="Paths to JSON files (2 or more)")
    args = parser.parse_args()

    deduplicate_and_merge(
        args.files,
        "merged.json",
        "duplicates.json"
    )
