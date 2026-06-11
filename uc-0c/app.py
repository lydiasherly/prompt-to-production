"""
UC-0C app.py — Growth calculator for ward budget data.
"""
import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional


def load_dataset(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        required = {"period", "ward", "category", "budgeted_amount", "actual_spend", "notes"}
        if not required.issubset(set(reader.fieldnames or [])):
            missing = required.difference(set(reader.fieldnames or []))
            raise ValueError(f"Input CSV is missing required columns: {', '.join(sorted(missing))}")
        return [row for row in reader]


def parse_float(value: str) -> Optional[float]:
    if value is None:
        return None
    clean = value.strip()
    if clean == "":
        return None
    try:
        return float(clean)
    except ValueError:
        return None


def compute_growth(rows: List[Dict[str, str]], ward: str, category: str, growth_type: str) -> List[Dict[str, str]]:
    filtered = [row for row in rows if row["ward"] == ward and row["category"] == category]
    if not filtered:
        raise ValueError(f"No rows found for ward '{ward}' and category '{category}'.")

    if growth_type != "MoM" and growth_type != "YoY":
        raise ValueError("Growth type must be either MoM or YoY.")

    sorted_rows = sorted(filtered, key=lambda r: r["period"])
    output = []
    previous = None
    for row in sorted_rows:
        actual = parse_float(row["actual_spend"])
        note = row.get("notes", "").strip()
        entry = {
            "period": row["period"],
            "ward": row["ward"],
            "category": row["category"],
            "actual_spend": row["actual_spend"].strip() or "NULL",
            "previous_actual_spend": "",
            "growth_type": growth_type,
            "growth_pct": "",
            "formula": "",
            "notes": note,
            "flag": "",
        }

        if actual is None:
            entry["growth_pct"] = "NULL"
            entry["formula"] = "Cannot compute growth because actual_spend is NULL."
            entry["flag"] = "NULL_ACTUAL"
        else:
            if growth_type == "MoM":
                entry["formula"] = "(current_actual - previous_actual) / previous_actual * 100"
                if previous is None or previous.get("actual") is None:
                    entry["growth_pct"] = "NULL"
                    entry["previous_actual_spend"] = "NULL"
                    entry["flag"] = "MISSING_PREVIOUS"
                    entry["formula"] = "Cannot compute MoM growth because previous month actual_spend is missing."
                else:
                    entry["previous_actual_spend"] = f"{previous['actual']:.1f}"
                    if previous["actual"] == 0:
                        entry["growth_pct"] = "NULL"
                        entry["flag"] = "DIV_BY_ZERO"
                        entry["formula"] = "Cannot compute MoM growth because previous month actual_spend is zero."
                    else:
                        growth = (actual - previous["actual"]) / previous["actual"] * 100
                        entry["growth_pct"] = f"{growth:+.1f}%"
            else:
                entry["formula"] = "YoY comparison not available in a single-year dataset."
                entry["growth_pct"] = "NULL"
                entry["flag"] = "NO_YOY_DATA"

        if entry["previous_actual_spend"] == "":
            entry["previous_actual_spend"] = "NULL"

        output.append(entry)
        previous = {"actual": actual}

    return output


def write_output(path: Path, rows: List[Dict[str, str]]):
    fieldnames = [
        "period",
        "ward",
        "category",
        "actual_spend",
        "previous_actual_spend",
        "growth_type",
        "growth_pct",
        "formula",
        "notes",
        "flag",
    ]
    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="UC-0C growth calculator")
    parser.add_argument("--input", required=True, help="Path to ward_budget.csv")
    parser.add_argument("--ward", required=True, help="Ward name to calculate growth for")
    parser.add_argument("--category", required=True, help="Budget category to calculate growth for")
    parser.add_argument("--growth-type", required=True, help="Growth type: MoM or YoY")
    parser.add_argument("--output", required=True, help="Path to write growth_output.csv")
    args = parser.parse_args()

    rows = load_dataset(Path(args.input))
    results = compute_growth(rows, args.ward, args.category, args.growth_type)
    write_output(Path(args.output), results)
    print(f"Done. Growth output written to {args.output}")


if __name__ == "__main__":
    main()
