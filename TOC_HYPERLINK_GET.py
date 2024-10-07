import re
import os
import psycopg2
from datetime import datetime
import configparser

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

# Insert newspaper data with TOC and hyperlink
def insert_newspaper(conn, title, publication_date, toc, hyperlink):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO Newspapers (title, publication_date, toc, hyperlink)
                VALUES (%s, %s, %s, %s)
                RETURNING newspaper_id;
                """, (title, publication_date, toc, hyperlink)
            )
            newspaper_id = cur.fetchone()[0]
            print(f"Newspaper inserted with ID: {newspaper_id}")
            return newspaper_id
    except psycopg2.Error as e:
        print(f"Error inserting newspaper: {e}")
        return None

# Extract Table of Contents and Hyperlink from the text
def extract_toc_and_hyperlink(text):
    # Use regex to capture the content between "Masthead" and the "Persistent Link" section
    toc_match = re.search(r'Masthead(.*?)Persistent Link', text, re.DOTALL)
    hyperlink_match = re.search(r'(https?://\S+)', text)

    # Extract TOC and Hyperlink
    toc = toc_match.group(1).strip() if toc_match else None
    hyperlink = hyperlink_match.group(0).strip() if hyperlink_match else None

    # Replace multiple spaces/newlines for better formatting
    if toc:
        toc = re.sub(r'\s+', ' ', toc)  # Replace newlines or extra spaces

    return toc, hyperlink

# Process each file in the directory
def process_files(input_directory):
    conn = connect_db()
    if conn is None:
        return  # Exit if the database connection fails

    for filename in os.listdir(input_directory):
        if filename.lower().endswith(".txt"):
            input_file_path = os.path.join(input_directory, filename)
            
            # Extract date from the filename
            date_match = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', filename)
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

            try:
                # Try reading the file with an alternative encoding (e.g., 'windows-1252')
                with open(input_file_path, 'r', encoding='windows-1252', errors='replace') as file:
                    file_text = file.read()

                # Extract TOC and hyperlink
                toc, hyperlink = extract_toc_and_hyperlink(file_text)

                if toc and hyperlink:
                    # Insert newspaper with TOC and hyperlink
                    insert_newspaper(conn, "Trinity Journal", publication_date, toc, hyperlink)

            except Exception as e:
                print(f"Error processing file {filename}: {e}")

    conn.close()

# Define the input directory containing the files
input_directory = r"C:\\Users\\SeanOffice\\Documents\\Trinity Journal Text"

# Process the files and populate the database with TOC and hyperlink data
process_files(input_directory)
