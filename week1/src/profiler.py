import sqlite3
from pathlib import Path


def run_data_profile(db_path: str) -> None:
    """
    Profile the jobs database and output data quality metrics.
    
    This function:
    1. Checks if the database exists
    2. Calculates total records
    3. Counts null values in job_title, company, and description
    4. Calculates average description length
    5. Finds shortest and longest descriptions with their details
    6. Outputs formatted data quality report
    
    Args:
        db_path: Path to the SQLite database file
    """
    db_file = Path(db_path)
    
    # Check if database exists
    if not db_file.exists():
        print(f"❌ Database not found at {db_path}")
        return
    
    try:
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        # Get total records
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total_records = cursor.fetchone()[0]
        
        # Get null counts
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN job_title IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN company IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN description IS NULL THEN 1 ELSE 0 END)
            FROM jobs
        """)
        null_job_title, null_company, null_description = cursor.fetchone()
        
        # Get average description length
        cursor.execute("SELECT AVG(LENGTH(description)) FROM jobs WHERE description IS NOT NULL")
        avg_desc_length = cursor.fetchone()[0]
        avg_desc_length = int(avg_desc_length) if avg_desc_length else 0
        
        # Get shortest description with details
        cursor.execute("""
            SELECT LENGTH(description), source_id, job_title
            FROM jobs
            WHERE description IS NOT NULL
            ORDER BY LENGTH(description) ASC
            LIMIT 1
        """)
        shortest = cursor.fetchone()
        shortest_length = shortest[0] if shortest else 0
        shortest_source_id = shortest[1] if shortest else "N/A"
        shortest_job_title = shortest[2] if shortest else "N/A"
        
        # Get longest description with details
        cursor.execute("""
            SELECT LENGTH(description), source_id, job_title
            FROM jobs
            WHERE description IS NOT NULL
            ORDER BY LENGTH(description) DESC
            LIMIT 1
        """)
        longest = cursor.fetchone()
        longest_length = longest[0] if longest else 0
        longest_source_id = longest[1] if longest else "N/A"
        longest_job_title = longest[2] if longest else "N/A"
        
        connection.close()
        
        # Format and print output
        print("\n--- 🔍 DATA QUALITY REPORT ---")
        print(f"📈 Total Records: {total_records}")
        print(f"❓ Missing Values -> job_title: {null_job_title}, company: {null_company}, description: {null_description}")
        print(f"📝 Avg Description Length: {avg_desc_length} chars")
        print(f"⚠️ Shortest Description: {shortest_length} chars")
        print(f"   ↳ source_id: {shortest_source_id} | job_title: {shortest_job_title}")
        print(f"🚨 Longest Description: {longest_length} chars")
        print(f"   ↳ source_id: {longest_source_id} | job_title: {longest_job_title}")
        print()
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")