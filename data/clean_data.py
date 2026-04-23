import csv
import re
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import RAW_DIR, CLEAN_DIR, CANONICAL_CATEGORIES, JUNK_KEYWORDS, JUNK_HEADLINE_PATTERNS

CLEAN_DIR.mkdir(parents=True, exist_ok=True)

REMOVE_PATTERNS = [
    r"continue reading",
    r"read more\b",
]


def normalize_category(cat: str) -> str:
    if not cat:
        return ""
    return CANONICAL_CATEGORIES.get(cat.strip().lower(), cat.strip())


def is_junk(headline: str, description: str) -> bool:
    text = f"{headline} {description}".lower()
    if any(kw in text for kw in JUNK_KEYWORDS):
        return True
    for pattern in JUNK_HEADLINE_PATTERNS:
        if re.search(pattern, headline.strip().lower()):
            return True
    return False


def clean_text(text: str) -> str:
    if not text:
        return ""
    for pattern in REMOVE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text.strip()


def clean_csv(input_file: Path, output_file: Path) -> None:
    print(f"\nProcessing: {input_file.name}")
    removed_rows = []

    with open(input_file, newline="", encoding="utf-8") as infile, \
         open(output_file, "w", newline="", encoding="utf-8") as outfile:

        reader = csv.DictReader(infile)
        if not reader.fieldnames:
            print(f"  Skipping {input_file.name} — empty or invalid.")
            return

        writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)
        writer.writeheader()

        kept = 0
        removed = 0

        for row in reader:
            row = {k: clean_text(v) for k, v in row.items()}
            headline = row.get("headline", "")
            description = row.get("description", "")

            if is_junk(headline, description):
                removed += 1
                removed_rows.append(headline)
                continue

            row["category"] = normalize_category(row.get("category", ""))
            writer.writerow(row)
            kept += 1

    print(f"  Kept: {kept} | Removed: {removed}")

    if removed_rows:
        for r in removed_rows[:5]:
            print(f"  - removed: {r}")
        if removed > 5:
            print(f"  ... and {removed - 5} more")


def main():
    csv_files = list(RAW_DIR.glob("*.csv"))
    if not csv_files:
        print(f"No CSV files found in {RAW_DIR}")
        return

    for csv_file in csv_files:
        output_file = CLEAN_DIR / f"{csv_file.stem}_clean.csv"
        clean_csv(csv_file, output_file)


if __name__ == "__main__":
    main()
