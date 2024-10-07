import os
import re
import psycopg2

import configparser
import torch

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU

# Database connection using psycopg2
# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')

# Access database settings from settings.ini
db_host = config['database']['host']
db_name = config['database']['database']
db_user = config['database']['user']
db_password = config['database']['password']
db_port = config['database']['port']

# Database connection using psycopg2
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

# Function to get or insert newspaper data
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

# Define regex to extract titles and content
article_pattern = re.compile(r'Title:\s*(.*?)\s*Body:\s*(.*?)(?=\nTitle:|\Z)', re.DOTALL)

def process_files_in_directory(directory_path):
    conn = connect_db()
    if not conn:
        return

    cursor = conn.cursor()

    # Iterate over all files in the directory
    for filename in os.listdir(directory_path):
        file_path = os.path.join(directory_path, filename)

        if os.path.isfile(file_path) and filename.endswith('.txt'):
            print(f"[INFO] Processing file: {filename}")

            # Assuming title and publication_date can be inferred from the filename or content
            title = "Trinity Journal"  # Adjust this if title varies by file
            # Extract publication_date from filename or file content
            # Assuming the publication_date can be extracted from filename
            date_match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', filename)
            if date_match:
                day = int(date_match.group(1))
                month = date_match.group(2)
                year = int(date_match.group(3))
                try:
                    publication_date = f"{day} {month} {year}"
                except ValueError:
                    print(f"[WARNING] Invalid date in filename: {filename}")
                    continue
            else:
                print(f"[WARNING] Could not extract publication date from filename: {filename}")
                continue

            # Get or insert the newspaper and get the ID
            newspaper_id = get_or_insert_newspaper(cursor, title, publication_date)
            if not newspaper_id:
                print(f"[ERROR] Unable to get or insert newspaper for file: {filename}")
                continue

            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Find all matches of titles and bodies
            matches = article_pattern.findall(content)

            for match in matches:
                article_title, body = match
                article_title = article_title.strip()
                body = body.strip()

                # Insert into database with reference to newspaper_id
                cursor.execute("""
                    INSERT INTO articles (title, content, newspaper_id)
                    VALUES (%s, %s, %s)
                """, (article_title, body, newspaper_id))

    # Commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()
    print("[INFO] Database updated successfully.")

# Replace with the directory path containing the text files
directory_path = "C:\\Users\\SeanOffice\\Documents\\Trinity Journal Segmented 3"
process_files_in_directory(directory_path)
