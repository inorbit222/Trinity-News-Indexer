#NER TO DATABASE SUMMARIES
import psycopg2
from transformers import pipeline
import logging
import configparser
from tqdm import tqdm  # For tracking progress
import torch

import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # Make sure GPU-1 is visible


# Check if CUDA is available
if torch.cuda.is_available():
    device = torch.device("cuda:0")  # Use the NVIDIA GPU (GPU-1)
    print("Using GPU:", torch.cuda.get_device_name(device))
else:
    device = torch.device("cpu")
    print("Using CPU")

# Load NER model with the specified device
ner_model = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english", device=device)



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

# Fetch summaries from the database
def fetch_summaries(cursor, batch_size=100, offset=0):
    cursor.execute("SELECT article_id, summary FROM articles WHERE summary IS NOT NULL LIMIT %s OFFSET %s", (batch_size, offset))
    return cursor.fetchall()

# Update the summaries column with NER entities
import json  # Import json module

# Update the summaries column with NER entities (stored as JSONB)
def update_summary_ner_entities(cursor, article_id, ner_entities):
    query = """
        UPDATE articles
        SET summary_ner_entities = %s
        WHERE article_id = %s;
    """
    # Convert ner_entities (list of dicts) to a JSON string
    cursor.execute(query, (json.dumps(ner_entities), article_id))


# Batch NER processing for summaries
def process_ner_summaries_in_batches(cursor, ner_model, batch_size=100):
    offset = 0
    total_summaries = 0

    while True:
        summaries = fetch_summaries(cursor, batch_size, offset)
        if not summaries:
            break  # Stop when no more summaries are fetched

        # Process each summary in the batch
        for article_id, summary in summaries:
            entities = ner_model(summary)

            # Group entities in a structured way for storing
            grouped_entities = [{"entity_type": entity['entity_group'], "entity_value": entity['word']} for entity in entities]

            # Update the article's summary with NER results
            update_summary_ner_entities(cursor, article_id, grouped_entities)

            total_summaries += 1

        logging.info(f"[INFO] Processed {total_summaries} summaries.")
        offset += batch_size

    logging.info("[INFO] NER processing on summaries completed.")

# Main NER pipeline for summaries
def run_ner_summaries_pipeline(batch_size=100):
    logging.info("[INFO] Starting the NER summaries pipeline...")

    conn = connect_db()
    if conn is None:
        return

    cursor = conn.cursor()
    ner_model = load_ner_model()

    process_ner_summaries_in_batches(cursor, ner_model, batch_size=batch_size)

    # Commit all changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()
    logging.info("[INFO] NER summaries pipeline completed successfully.")

# Execute the NER summaries pipeline
if __name__ == "__main__":
    run_ner_summaries_pipeline(batch_size=100)

