import psycopg2
from transformers import pipeline
import logging
import configparser
from tqdm import tqdm  # For tracking progress
import torch

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU
print(f"Using device: {'GPU' if device == 0 else 'CPU'}")
# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load a pretrained NER pipeline from Hugging Face and specify the device
nlp = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", device=device)


# Load NER model (using a larger model may require GPU resources)
def load_ner_model():
    return pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", grouped_entities=True)

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')

# Database credentials
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
        logging.info("[INFO] Connected to the database.")
        return conn
    except psycopg2.Error as e:
        logging.error(f"[ERROR] Could not connect to the database: {e}")
        return None

# Fetch articles from the database
def fetch_articles(cursor, batch_size=100, offset=0):
    cursor.execute("SELECT article_id, content FROM articles LIMIT %s OFFSET %s", (batch_size, offset))
    return cursor.fetchall()

# Insert entities into the database in bulk
def insert_entities(cursor, entity_data):
    query = """
        INSERT INTO entities (article_id, entity_type, entity_value, start_pos, end_pos)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (article_id, entity_type, entity_value, start_pos, end_pos) DO NOTHING;

        """
    cursor.executemany(query, entity_data)

# Batch NER processing
def process_ner_in_batches(cursor, ner_model, batch_size=100):
    offset = 0
    total_articles = 0
    entity_data = []
    
    while True:
        articles = fetch_articles(cursor, batch_size, offset)
        if not articles:
            break  # Stop when no more articles are fetched

        # Process each article in the batch
        for article_id, content in articles:
            entities = ner_model(content)
            for entity in entities:
                entity_type = entity['entity_group']
                entity_value = entity['word']
                start_pos = entity['start']
                end_pos = entity['end']
                entity_data.append((article_id, entity_type, entity_value, start_pos, end_pos))

            total_articles += 1
            if len(entity_data) >= batch_size:
                insert_entities(cursor, entity_data)
                entity_data = []  # Reset after inserting

        logging.info(f"[INFO] Processed {total_articles} articles.")
        offset += batch_size

    # Insert any remaining entity data
    if entity_data:
        insert_entities(cursor, entity_data)

    logging.info("[INFO] NER processing completed.")

# Main NER pipeline
def run_ner_pipeline(batch_size=100):
    logging.info("[INFO] Starting the NER pipeline...")

    conn = connect_db()
    if conn is None:
        return

    cursor = conn.cursor()
    ner_model = load_ner_model()

    process_ner_in_batches(cursor, ner_model, batch_size=batch_size)

    # Commit all changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()
    logging.info("[INFO] NER pipeline completed successfully.")

# Execute the NER pipeline
if __name__ == "__main__":
    run_ner_pipeline(batch_size=100)
