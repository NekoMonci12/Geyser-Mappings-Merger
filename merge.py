import json
import argparse
import os

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def deduplicate_and_merge(file1, file2, out1, out2, merged_out, duplicates_out):
    data1 = load_json(file1)
    data2 = load_json(file2)

    items1, items2 = data1["items"], data2["items"]

    duplicates = {"format_version": "1", "items": {}}
    duplicates_exact = {}  # {(name, id): entry}
    duplicates_name = set()
    duplicates_id = set()

    # Find duplicates between file1 and file2
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
                        # only add once
                        if not any(d["name"] == e["name"] and d["custom_model_data"] == e["custom_model_data"]
                                   for d in duplicates["items"][item_type]):
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

    # Clean both files
    data1["items"] = filter_items(items1)
    data2["items"] = filter_items(items2)

    # Collect one copy of exact duplicates
    filter_items(items1, collect_duplicates=True)
    filter_items(items2, collect_duplicates=True)

    # Merge cleaned sets
    merged = {"format_version": "1", "items": {}}
    for items_dict in (data1["items"], data2["items"]):
        for item_type, entries in items_dict.items():
            merged["items"].setdefault(item_type, []).extend(entries)

    # Save outputs
    save_json(data1, out1)
    save_json(data2, out2)
    save_json(merged, merged_out)
    save_json(duplicates, duplicates_out)

    print(f"✅ Cleaned {file1} → {out1}")
    print(f"✅ Cleaned {file2} → {out2}")
    print(f"✅ Merged output → {merged_out}")
    print(f"✅ Unique exact duplicates saved → {duplicates_out}")
    print(f"❌ Removed same-name dif-ID: {duplicates_name}")
    print(f"❌ Removed same-ID dif-name: {duplicates_id}")
    print(f"⚠️ Moved exact duplicates (unique): {list(duplicates_exact.keys())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deduplicate and merge JSON mapping files.")
    parser.add_argument("file1", help="Path to first JSON file")
    parser.add_argument("file2", help="Path to second JSON file")
    args = parser.parse_args()

    # Auto-generate output filenames based on input names
    base1 = os.path.splitext(os.path.basename(args.file1))[0]
    base2 = os.path.splitext(os.path.basename(args.file2))[0]

    deduplicate_and_merge(
        args.file1,
        args.file2,
        f"{base1}_clean.json",
        f"{base2}_clean.json",
        "merged.json",
        "duplicates.json"
    )
