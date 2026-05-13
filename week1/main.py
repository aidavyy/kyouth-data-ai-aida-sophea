import sys
from src.ingestor import ingest_all_mhtml
from src.processor import process_all_html


def main():
    """Main entry point for CLI orchestration."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <command>")
        print("Commands:")
        print("  ingest  - Extract HTML from MHTML files (Bronze Layer)")
        print("  process - Clean HTML and save JSON files (Silver Layer)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "ingest":
        ingest_all_mhtml("data/0_source", "data/1_bronze")
    elif command == "process":
        process_all_html("data/1_bronze", "data/2_silver")
    else:
        print(f"Unknown command: {command}")
        print("Usage: python main.py <command>")
        print("Commands:")
        print("  ingest  - Extract HTML from MHTML files (Bronze Layer)")
        print("  process - Clean HTML and save JSON files (Silver Layer)")
        sys.exit(1)


if __name__ == "__main__":
    main()