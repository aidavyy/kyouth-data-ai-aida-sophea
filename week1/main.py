import sys
from pathlib import Path

from src.ingestor import ingest_all_mhtml
from src.processor import process_all_html
from src.loader import load_all_jsons
from src.profiler import run_data_profile


def main():
    """Main entry point for CLI orchestration."""
    if len(sys.argv) < 2:
        print("Usage: python main.py [ingest|process|load|profile|all]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "ingest":
        ingest_all_mhtml("data/0_source", "data/1_bronze")
    elif command == "process":
        process_all_html("data/1_bronze", "data/2_silver")
    elif command == "load":
        load_all_jsons("data/2_silver", "data/3_gold")
    elif command == "profile":
        db_path = Path("data/3_gold/jobs.db")
        run_data_profile(str(db_path))
    elif command == "all":
        print("Starting full ETL pipeline...")
        print("\n--- INGEST ---")
        ingest_all_mhtml("data/0_source", "data/1_bronze")
        print("\n--- PROCESS ---")
        process_all_html("data/1_bronze", "data/2_silver")
        print("\n--- LOAD ---")
        load_all_jsons("data/2_silver", "data/3_gold")
        print("\n--- PROFILE ---")
        db_path = Path("data/3_gold/jobs.db")
        run_data_profile(str(db_path))
        print("\nFull ETL pipeline completed!")
    else:
        print(f"Unknown command: {command}")
        print("Usage: python main.py [ingest|process|load|profile|all]")
        sys.exit(1)


if __name__ == "__main__":
    main()