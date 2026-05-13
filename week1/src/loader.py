import json
import sqlite3
from pathlib import Path


def load_all_jsons(input_dir: str, output_dir: str) -> dict:
    """
    Load Silver JSON data into SQLite database (Gold Layer).
    
    This function:
    1. Creates the 3_gold directory if it doesn't exist
    2. Initializes SQLite database with jobs table
    3. Loads all JSON files from input_dir
    4. Inserts records with idempotency using INSERT OR IGNORE
    5. Tracks inserted, skipped (duplicate), and failed records
    
    Args:
        input_dir: Path to directory containing Silver JSON files
        output_dir: Path to directory where jobs.db will be created
    
    Returns:
        Dictionary with statistics: {'total': int, 'inserted': int, 'skipped': int}
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Database path
    db_path = output_path / "jobs.db"
    
    # Initialize statistics
    total = 0
    inserted = 0
    skipped = 0
    
    print("🥇 Gold:...")
    
    # Handle case where input directory doesn't exist
    if not input_path.exists():
        print(f"⚠️ Input directory not found: {input_dir}")
        print(f"\n📊 Gold Summary:")
        print(f"Total: {total} | Inserted: {inserted} | Skipped: {skipped}")
        return {"total": total, "inserted": inserted, "skipped": skipped}
    
    # Connect to SQLite database
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    
    # Create jobs table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            source_id TEXT PRIMARY KEY,
            job_title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT NOT NULL,
            tech_stack TEXT
        )
    """)
    connection.commit()
    
    # Get all JSON files from input directory
    json_files = sorted(input_path.glob("*.json"))
    
    # Load each JSON file
    for json_file in json_files:
        total += 1
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Insert record with INSERT OR IGNORE for idempotency
            cursor.execute(
                """
                INSERT OR IGNORE INTO jobs (source_id, job_title, company, description)
                VALUES (?, ?, ?, ?)
                """,
                (
                    data.get("source_id"),
                    data.get("job_title"),
                    data.get("company"),
                    data.get("description"),
                ),
            )
            
            # Check if record was inserted or skipped
            if cursor.rowcount > 0:
                print(f"✅ Inserted: {json_file.stem}.json")
                inserted += 1
            else:
                print(f"⏭️ Skipped (duplicate): {json_file.stem}.json")
                skipped += 1
        
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"❌ Failed: {json_file.stem}.json ({str(e)})")
            skipped += 1
    
    # Commit changes and close connection
    connection.commit()
    connection.close()
    
    # Print summary
    print(f"\n📊 Gold Summary:")
    print(f"Total: {total} | Inserted: {inserted} | Skipped: {skipped}")
    
    return {"total": total, "inserted": inserted, "skipped": skipped}