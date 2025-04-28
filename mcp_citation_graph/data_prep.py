import ijson
import json
from decimal import Decimal
from tqdm import tqdm
import pandas as pd


def process_dblp():
    input_path = 'data/dblp.v12.json'
    output_path = 'data/dblp.filtered.json'

    with open(input_path, 'r', encoding='utf-8') as infile:
        total_entries = sum(1 for _ in ijson.items(infile, 'item'))

    count = 0
    valid_doc_types = {"Conference", "Journal", "Book"}
    with open(input_path, 'r', encoding='utf-8') as infile, open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write('[\n')
        first = True
        for entry in tqdm(ijson.items(infile, 'item'), total=total_entries, desc="Filtering entries"):
            if "references" in entry and entry.get("doc_type") in valid_doc_types:
                for k in ["page_start", "page_end", "volume", "issue", "doi", "indexed_abstract"]:
                    if k in entry:
                        del entry[k]
                
                entry["n_references"] = len(entry["references"])

                if "authors" in entry and isinstance(entry["authors"], list):
                    entry["author_names"] = [author.get("name", "") for author in entry["authors"]]
                    entry["author_orgs"] = [author.get("org", "") for author in entry["authors"]]
                    entry["author_ids"] = [author.get("id", "") for author in entry["authors"]]
                    del entry["authors"]

                if "venue" in entry and isinstance(entry["venue"], dict):
                    entry["venue_name"] = entry["venue"].get("raw", "")
                    entry["venue_id"] = entry["venue"].get("id", "")
                    entry["venue_type"] = entry["venue"].get("type", "")
                    del entry["venue"]

                if "fos" in entry and isinstance(entry["fos"], list):
                    entry["fos_names"] = [fos_item.get("name", "") for fos_item in entry["fos"]]
                    entry["fos_ws"] = [fos_item.get("w", None) for fos_item in entry["fos"]]
                    del entry["fos"]

                if not first:
                    outfile.write(',\n')
                json.dump(entry, outfile, ensure_ascii=False, default=lambda o: float(o) if isinstance(o, Decimal) else o)
                first = False
                count += 1
        outfile.write('\n]')
    print(f"Filtered {count} entries out of {total_entries} and written to {output_path}")

    with open(output_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    entries = [entry for entry in entries if entry.get('year', 0) >= 2000 and entry.get('n_references', 0) > 8 and (entry.get('year', 0) > 2018 or entry.get('n_citation', 0) > 4)]
    with open('data/dblp.filtered.y2000_r9_c5.json', 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=4, ensure_ascii=False, default=lambda o: float(o) if isinstance(o, Decimal) else o)
    print(f"Second filtering: {len(entries)} entries out of {count} and written to 'data/dblp.filtered.y2000_r9_c5.json'")


if __name__ == "__main__":
    process_dblp()
