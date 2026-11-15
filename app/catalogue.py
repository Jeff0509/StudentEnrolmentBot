
import json
from pathlib import Path

from app.metadata import extract_database_metadata
from app.relationships import extract_foreign_keys


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_catalogue():

    print("Building WideWorldImporters database catalogue...")

    # Extract tables, columns and primary keys
    metadata = extract_database_metadata()

    # Extract declared foreign-key relationships
    relationships = extract_foreign_keys()

    catalogue = {
        "database": "WideWorldImporters",
        "tables": metadata,
        "relationships": relationships
    }

    output_file = PROJECT_ROOT / "database_catalogue.json"

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            catalogue,
            file,
            indent=4,
            ensure_ascii=False,
            default=str
        )

    print("\n--------------------------------")
    print("DATABASE CATALOGUE CREATED")
    print("--------------------------------")
    print(f"Database: WideWorldImporters")
    print(f"Tables: {len(metadata)}")
    print(f"Relationships: {len(relationships)}")
    print(f"File: {output_file}")


if __name__ == "__main__":
    build_catalogue()
