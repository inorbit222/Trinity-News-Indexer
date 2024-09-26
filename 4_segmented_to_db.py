import os
import re
import psycopg2
from datetime import datetime
import configparser

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')

# Access database settings from settings.ini
db_host = config['database']['host']
db_name = config['database']['database']
db_user = config['database']['user']
db_password = config['database']['password']
db_port = config['database']['port']

# Connect to the PostgreSQL database
def connect_db():
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        print("[INFO] Database connection successful.")
        return conn
    except psycopg2.Error as e:
        print(f"[ERROR] Could not connect to the database: {e}")
        return None

# Insert newspaper data if not already present
def get_or_insert_newspaper(cursor, title, publication_date):
    try:
        cursor.execute("""
            SELECT newspaper_id FROM newspapers WHERE title = %s AND publication_date = %s;
        """, (title, publication_date))
        result = cursor.fetchone()

        if result:
            return result[0]
        else:
            cursor.execute("""
                INSERT INTO newspapers (title, publication_date)
                VALUES (%s, %s) RETURNING newspaper_id;
            """, (title, publication_date))
            newspaper_id = cursor.fetchone()[0]
            print(f"[INFO] Inserted newspaper with ID: {newspaper_id}")
            return newspaper_id
    except psycopg2.Error as e:
        print(f"[ERROR] Error inserting newspaper: {e}")
        return None

# Insert article into the database
def insert_articles(cursor, articles):
    try:
        # Batch insert articles
        cursor.executemany("""
            INSERT INTO articles (newspaper_id, title, content)
            VALUES (%s, %s, %s);
        """, articles)
        print(f"[INFO] Inserted {len(articles)} articles.")
    except psycopg2.Error as e:
        print(f"[ERROR] Error inserting articles: {e}")

# Process and extract articles from a single file
def process_file(file_path, cursor):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_text = file.read()

        # Extract publication date from filename or file content
        date_match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', file_path)
        if date_match:
            day = int(date_match.group(1))
            month = date_match.group(2)
            year = int(date_match.group(3))
            try:
                publication_date = datetime.strptime(f'{day} {month} {year}', '%d %B %Y').date()
            except ValueError:
                publication_date = datetime(1900, 1, 1).date()
        else:
            publication_date = datetime(1900, 1, 1).date()

        # Use a static newspaper title for this example (update as needed)
        title = "Trinity Journal"

        # Retrieve or insert the newspaper
        newspaper_id = get_or_insert_newspaper(cursor, title, publication_date)

        # Define regex to extract article titles and bodies
        article_pattern = re.compile(r'(?<=\n\n)([^\n]{1,80})\n+([^\n]+\n(.+\n)*)')

        # Extract articles
        matches = list(article_pattern.finditer(file_text))

        articles = []
        for match in matches:
            article_title = match.group(1)
            article_body = match.group(2)
            articles.append((newspaper_id, article_title, article_body))

        # Insert articles into the database
        insert_articles(cursor, articles)

    except Exception as e:
        print(f"[ERROR] Error processing file {file_path}: {e}")

# Process all files in the directory
def process_files(input_directory):
    conn = connect_db()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        for filename in os.listdir(input_directory):
            if filename.lower().endswith(".txt"):
                file_path = os.path.join(input_directory, filename)
                print(f"[INFO] Processing file: {file_path}")
                process_file(file_path, cursor)

        # Commit all changes at once
        conn.commit()
        print("[INFO] All files processed and changes committed.")
    except Exception as e:
        print(f"[ERROR] Error processing files: {e}")
        conn.rollback()  # Rollback in case of error
    finally:
        cursor.close()
        conn.close()
        print("[INFO] Database connection closed.")

# Main entry point
if __name__ == "__main__":
    input_directory = r"C:\\Users\\SeanOffice\\Documents\\Trinity Journal Segmented 3"  # Update the input directory path
    process_files(input_directory)
