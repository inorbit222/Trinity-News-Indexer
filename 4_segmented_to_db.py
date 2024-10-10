import os
import re
import psycopg2
import configparser
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')

# Database credentials
db_host = config['database']['host']
db_name = config['database']['database']
db_user = config['database']['user']
db_password = config['database']['password']
db_port = config['database']['port']

# Input directory for segmented articles
input_directory = r"C:\Users\SeanOffice\Documents\Trinity Journal Segmented 3"

# Function to connect to the PostgreSQL database
def connect_db():
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        logging.info("[INFO] Connected to the database.")
        return conn
    except psycopg2.Error as e:
        logging.error(f"[ERROR] Could not connect to the database: {e}")
        return None

# Function to extract the publication date from the file name (or set a default if not found)
def extract_publication_date(file_name):
    date_match = re.search(r'\d{1,2}\s\w+\s\d{4}', file_name)
    if date_match:
        publication_date = date_match.group(0)
        logging.info(f"[INFO] Extracted publication date: {publication_date}")
        return publication_date
    else:
        logging.warning(f"[WARNING] Could not parse date from file {file_name}. Defaulting to 'Unknown Date'.")
        return "Unknown Date"

# Function to process a single file and insert articles into the database
def process_file(file_path, conn, newspaper_id):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_contents = file.read()
    
    cursor = conn.cursor()

    # Regex pattern to identify articles with title and body
    article_pattern = re.compile(r'Title:\s*(.*?)\s*Body:\s*(.*?)(?=\nTitle:|\Z)', re.DOTALL)

    # Find all articles in the file
    matches = article_pattern.findall(file_contents)
    
    # Check if there are valid articles in the file
    if not matches:
        logging.warning(f"[WARNING] No valid articles found in {file_path}. Skipping file.")
        return

    # Process each article and insert into the database
    for match in matches:
        title = match[0].strip() if match[0].strip() != "" else "Untitled"
        body = match[1].strip()

        # Log missing or untitled articles
        if title == "Untitled":
            logging.warning(f"[WARNING] Missing title in file {file_path}. Defaulting to 'Untitled'.")

        # Insert article into the database, using ON CONFLICT to avoid duplicates
        try:
            cursor.execute("""
                INSERT INTO Articles (newspaper_id, title, content, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (newspaper_id, title) DO NOTHING;
            """, (newspaper_id, title, body))
            conn.commit()
            logging.info(f"[INFO] Article inserted with title: {title}")

        except psycopg2.Error as e:
            logging.error(f"[ERROR] Failed to insert article with title {title}: {e}")
            conn.rollback()

    cursor.close()

# Function to get the newspaper ID from the database, or create a new entry if it doesn't exist
def get_newspaper_id(conn, file_name, publication_date):
    cursor = conn.cursor()

    try:
        # Check if the newspaper already exists
        cursor.execute("""
            SELECT newspaper_id FROM Newspapers WHERE title = %s AND publication_date = %s;
        """, (file_name, publication_date))
        result = cursor.fetchone()

        if result:
            newspaper_id = result[0]
            logging.info(f"[INFO] Found existing newspaper entry with ID {newspaper_id}.")
        else:
            # Insert a new newspaper record
            cursor.execute("""
                INSERT INTO Newspapers (title, publication_date, created_at)
                VALUES (%s, %s, NOW()) RETURNING newspaper_id;
            """, (file_name, publication_date))
            newspaper_id = cursor.fetchone()[0]
            conn.commit()
            logging.info(f"[INFO] Inserted new newspaper entry with ID {newspaper_id}.")

    except psycopg2.Error as e:
        logging.error(f"[ERROR] Failed to get or insert newspaper: {e}")
        conn.rollback()
        newspaper_id = None

    cursor.close()
    return newspaper_id

# Main function to iterate over files and process them
def process_all_files():
    # Connect to the database
    conn = connect_db()
    if conn is None:
        logging.error("[ERROR] Could not establish a database connection. Exiting.")
        return

    # Loop through all text files in the input directory
    for file_name in os.listdir(input_directory):
        if file_name.lower().endswith(".txt"):
            file_path = os.path.join(input_directory, file_name)
            
            logging.info(f"[INFO] Processing file: {file_name}")

            # Extract publication date from file name (or set a default)
            publication_date = extract_publication_date(file_name)

            # Get or create the newspaper entry and retrieve its ID
            newspaper_id = get_newspaper_id(conn, file_name, publication_date)

            if newspaper_id:
                # Process the file and insert its articles into the database
                process_file(file_path, conn, newspaper_id)

    # Close the database connection after processing all files
    conn.close()
    logging.info("[INFO] All files processed and database connection closed.")

# Run the script
if __name__ == "__main__":
    process_all_files()
