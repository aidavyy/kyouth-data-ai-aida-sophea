import sys
from src.ingestor import ingest_all_mhtml


def main():
    """Main entry point for CLI orchestration."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <command>")
        print("Commands:")
        print("  ingest - Extract HTML from MHTML files (Bronze Layer)")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Route commands
    if command == "ingest":
        input_dir = "data/0_source"
        output_dir = "data/1_bronze"
        ingest_all_mhtml(input_dir, output_dir)
    else:
        print(f"Unknown command: {command}")
        print("Usage: python main.py <command>")
        print("Commands:")
        print("  ingest - Extract HTML from MHTML files (Bronze Layer)")
        sys.exit(1)


if __name__ == "__main__":
    main()