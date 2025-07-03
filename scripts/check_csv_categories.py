import argparse
import csv
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("csv_path")

args = parser.parse_args()
path = args.csv_path
with open(path, newline="") as f:
    reader = csv.DictReader(f)
    # Show detected columns to debug header issues
    print("Detected columns:", reader.fieldnames)
    # Count using get to avoid KeyError
    cats = Counter()
    for row in reader:
        val = row.get("Category")
        if val is None:
            # skip rows without Category field
            continue
        cats[val.strip()] += 1

print("CSV categories and counts:")
for cat, cnt in cats.most_common():
    print(f"  {cat!r}: {cnt}")

csv_set = set(cats.keys())

from categories import categories  
code_set = set(categories)

print("\nDiscrepancies:")
print("In CSV but NOT in code:", csv_set - code_set)
print("In code but NOT in CSV:", code_set - csv_set)