import ijson
import json
from decimal import Decimal
from tqdm import tqdm


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
                if not first:
                    outfile.write(',\n')
                json.dump(entry, outfile, ensure_ascii=False, default=lambda o: float(o) if isinstance(o, Decimal) else o)
                first = False
                count += 1
        outfile.write('\n]')
    print(f"Filtered {count} entries written to {output_path}")


if __name__ == "__main__":
    process_dblp()
