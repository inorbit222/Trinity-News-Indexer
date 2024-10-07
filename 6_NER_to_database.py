import logging
import psycopg2
from transformers import pipeline
from psycopg2 import sql
import re
import torch

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU

# Load a pretrained NER pipeline from Hugging Face and specify the device
nlp = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", device=device)

print(f"Using device: {'GPU' if device == 0 else 'CPU'}")

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        logging.info("Database connection successful.")
        return conn
    except psycopg2.Error as e:
        logging.error(f"Could not connect to the database: {e}")
        return None

# Step 2: Create necessary tables (if they don't exist)
def create_tables(cursor):
    logging.info("Creating 'articles' and 'entities' tables if they don't exist...")
    try:
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
        logging.info("Tables created or already exist.")
    except Exception as e:
        logging.error(f"Error creating tables: {e}")

# Step 3: Clean and preprocess article content
def clean_text(text):
    # Convert to lowercase
    text = text.lower()
    # Remove non-alphabetic characters (keep letters and spaces)
    text = re.sub(r'[^a-z\s]', '', text)
    # Normalize spaces (remove extra spaces)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# Step 4: Combine consecutive NER tokens of the same type (multi-word entities)
def combine_entities(entities):
    combined_entities = []
    current_entity = None

    for entity in entities:
        if current_entity is None:
            current_entity = entity
        elif entity['entity'] == current_entity['entity'] and entity['start'] == current_entity['end'] + 1:
            # Extend current entity if the next token is a continuation (same type and adjacent)
            current_entity['word'] += ' ' + entity['word']
            current_entity['end'] = entity['end']
        else:
            combined_entities.append(current_entity)
            current_entity = entity

    # Append the last entity
    if current_entity:
        combined_entities.append(current_entity)

    return combined_entities

# Step 5: Fetch articles from the database in batches
def fetch_articles(cursor, batch_size=100):
    logging.info("Fetching articles from the 'articles' table in batches...")
    try:
        cursor.execute("SELECT COUNT(*) FROM articles")
        total_articles = cursor.fetchone()[0]
        logging.info(f"Total articles found: {total_articles}")

        offset = 0
        while offset < total_articles:
            cursor.execute(sql.SQL("SELECT article_id, content FROM articles LIMIT %s OFFSET %s"), (batch_size, offset))
            articles = cursor.fetchall()
            logging.info(f"Fetched {len(articles)} articles in batch.")
            yield articles
            offset += batch_size
    except Exception as e:
        logging.error(f"Error fetching articles: {e}")
        yield []

# Step 6: Insert extracted entities into the 'entities' table
def store_entities(cursor, article_id, entities):
    logging.info(f"Storing entities for article ID {article_id}...")
    try:
        for entity in entities:
            # Validate that entity values are meaningful (optional: ignore very short entities)
            if len(entity['word']) > 1:  # Discard trivial one-character entities
                cursor.execute("""
                    INSERT INTO entities (article_id, entity_type, entity_value, start_pos, end_pos)
                    VALUES (%s, %s, %s, %s, %s)
                """, (article_id, entity['entity'], entity['word'], entity['start'], entity['end']))
        logging.info(f"Entities stored for article ID {article_id}.")
    except Exception as e:
        logging.error(f"Error storing entities for article ID {article_id}: {e}")

# Step 7: Process each batch of articles, apply NER, and store results
def process_articles(cursor, conn, batch_size=100):
    for articles_batch in fetch_articles(cursor, batch_size):
        for article_id, content in articles_batch:
            try:
                logging.info(f"Processing article ID {article_id}...")

                # Clean the content before applying NER
                cleaned_content = clean_text(content)
                
                # Apply NER model to article content
                ner_results = nlp(cleaned_content)
                logging.info(f"Found {len(ner_results)} entities in article ID {article_id}.")
                
                # Combine multi-word entities
                combined_entities = combine_entities(ner_results)
                
                # Store the extracted entities in the database
                store_entities(cursor, article_id, combined_entities)
                
                # Commit after each article to ensure data consistency
                conn.commit()
            except Exception as e:
                logging.error(f"Error processing article ID {article_id}: {e}")

# Main Function
if __name__ == "__main__":
    # Connect to the database
    conn = connect_db()
    if conn:
        cursor = conn.cursor()

        # Create tables if they don't exist
        create_tables(cursor)

        # Process articles in batches and store NER results
        process_articles(cursor, conn, batch_size=100)

        # Close the connection after everything is done
        cursor.close()
        conn.close()
        logging.info("Database connection closed.")
    else:
        logging.error("Could not establish a database connection.")
