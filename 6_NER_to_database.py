import psycopg2
from transformers import pipeline

# Load a pretrained NER pipeline from Hugging Face
# Model is fine-tuned for extracting named entities (e.g., PERSON, ORG, LOC)
nlp = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

# Step 1: Connect to your PostgreSQL database
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

# Connect to PostgreSQL database
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

# Step 2: Create necessary tables (if they don't exist)
def create_tables(cursor):
    print("[INFO] Creating 'articles' and 'entities' tables if they don't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS articles (
        article_id SERIAL PRIMARY KEY,
        title TEXT,
        content TEXT
    );
    
    CREATE TABLE IF NOT EXISTS entities (
        entity_id SERIAL PRIMARY KEY,
        article_id INT REFERENCES articles(article_id),
        entity_type VARCHAR(255),
        entity_value VARCHAR(255),
        start_pos INT,
        end_pos INT
    );
    """)
    conn.commit()
    print("[INFO] Tables created or already exist.")

# Step 3: Fetch articles from the database
def fetch_articles(cursor):
    print("[INFO] Fetching articles from the 'articles' table...")
    cursor.execute("SELECT article_id, content FROM articles")
    articles = cursor.fetchall()
    print(f"[INFO] Retrieved {len(articles)} articles.")
    return articles

# Step 4: Insert extracted entities into the 'entities' table
def store_entities(cursor, article_id, entities):
    print(f"[INFO] Storing entities for article ID {article_id}...")
    for entity in entities:
        cursor.execute("""
            INSERT INTO entities (article_id, entity_type, entity_value, start_pos, end_pos)
            VALUES (%s, %s, %s, %s, %s)
        """, (article_id, entity['entity'], entity['word'], entity['start'], entity['end']))
    print(f"[INFO] Entities stored for article ID {article_id}.")
    conn.commit()

# Step 5: Process each article, apply NER, and store results
def process_articles(cursor):
    articles = fetch_articles(cursor)
    for article_id, content in articles:
        print(f"[INFO] Processing article ID {article_id}...")
        
        # Apply NER model to article content
        ner_results = nlp(content)
        print(f"[INFO] Found {len(ner_results)} entities in article ID {article_id}.")
        
        # Store the extracted entities in the database
        store_entities(cursor, article_id, ner_results)

# Main Function
if __name__ == "__main__":
    # Connect to the database
    conn = connect_db()
    if conn:
        cursor = conn.cursor()

        # Create tables if they don't exist
        create_tables(cursor)

        # Process articles and store NER results
        process_articles(cursor)

        # Close the connection after everything is done
        cursor.close()
        conn.close()
        print("[INFO] Database connection closed.")
    else:
        print("[ERROR] Could not establish a database connection.")
