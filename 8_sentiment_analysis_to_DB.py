import psycopg2
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re
import logging
import configparser

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize the VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

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

# Step 2: Create table for storing entity-level sentiment data
def create_sentiment_table(conn, cursor):
    try:
        logging.info("Creating 'entity_sentiments' table if it doesn't exist...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS entity_sentiments (
            id SERIAL PRIMARY KEY,
            entity_id INT REFERENCES entities(id),
            sentiment_pos FLOAT,
            sentiment_neg FLOAT,
            sentiment_neu FLOAT,
            sentiment_compound FLOAT
        );
        """)
        conn.commit()
        logging.info("'entity_sentiments' table is ready.")
    except Exception as e:
        logging.error(f"Error creating 'entity_sentiments' table: {e}")

# Step 3: Fetch entities and corresponding article content to populate surrounding sentences
def fetch_entities_with_articles(cursor, batch_size=100):
    try:
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_entities = cursor.fetchone()[0]
        logging.info(f"Total entities found: {total_entities}")
        
        offset = 0
        while offset < total_entities:
            cursor.execute("""
                SELECT e.entity_id, e.entity_value, a.content
                FROM entities e
                JOIN articles a ON e.article_id = a.article_id
                LIMIT %s OFFSET %s
            """, (batch_size, offset))
            entities = cursor.fetchall()
            logging.info(f"Fetched {len(entities)} entities in batch.")
            yield entities
            offset += batch_size
    except Exception as e:
        logging.error(f"Error fetching entities: {e}")


# Step 4: Function to extract the surrounding sentence for an entity within the article content
def extract_surrounding_sentence(entity, content):
    pattern = rf"([^.]*?{re.escape(entity)}[^.]*\.)"
    match = re.search(pattern, content)
    return match.group(0) if match else None

# Step 5: Update the surrounding_sentence field in the database
def update_surrounding_sentence(cursor, entity_id, surrounding_sentence):
    try:
        cursor.execute("""
            UPDATE entities
            SET surrounding_sentence = %s
            WHERE id = %s
        """, (surrounding_sentence, entity_id))
    except Exception as e:
        logging.error(f"Error updating surrounding sentence for entity ID {entity_id}: {e}")

# Step 6: Populate surrounding sentences for entities in batches
def populate_surrounding_sentences(cursor, conn, batch_size=100):
    for entities_batch in fetch_entities_with_articles(cursor, batch_size):
        for entity_id, entity_value, article_content in entities_batch:
            surrounding_sentence = extract_surrounding_sentence(entity_value, article_content)
            if surrounding_sentence:
                update_surrounding_sentence(cursor, entity_id, surrounding_sentence)
                logging.info(f"Updated entity ID {entity_id} with surrounding sentence.")
            else:
                logging.warning(f"No surrounding sentence found for entity ID {entity_id}.")
        conn.commit()

# Step 7: Fetch entities for sentiment analysis
def fetch_entities_for_sentiment(cursor):
    try:
        cursor.execute("SELECT id, entity_value, surrounding_sentence FROM entities WHERE surrounding_sentence IS NOT NULL")
        entities = cursor.fetchall()
        logging.info(f"Retrieved {len(entities)} entities with surrounding sentences for sentiment analysis.")
        return entities
    except Exception as e:
        logging.error(f"Error fetching entities for sentiment analysis: {e}")
        return []

# Step 8: Analyze sentiment for each entity using VADER
def analyze_entity_sentiment(entity_text):
    sentiment_scores = analyzer.polarity_scores(entity_text)
    return sentiment_scores['pos'], sentiment_scores['neg'], sentiment_scores['neu'], sentiment_scores['compound']

# Step 9: Store sentiment data in PostgreSQL
def store_entity_sentiment(conn, cursor, entity_id, pos, neg, neu, compound):
    try:
        cursor.execute("""
            INSERT INTO entity_sentiments (entity_id, sentiment_pos, sentiment_neg, sentiment_neu, sentiment_compound)
            VALUES (%s, %s, %s, %s, %s)
        """, (entity_id, pos, neg, neu, compound))
        conn.commit()
    except Exception as e:
        logging.error(f"Error storing sentiment for entity ID {entity_id}: {e}")

# Step 10: Process entities for sentiment analysis and store results
def process_entity_sentiments(conn, cursor):
    entities = fetch_entities_for_sentiment(cursor)
    for entity_id, entity_value, surrounding_sentence in entities:
        logging.info(f"Analyzing sentiment for entity '{entity_value}' (ID: {entity_id})...")
        pos, neg, neu, compound = analyze_entity_sentiment(surrounding_sentence)
        logging.info(f"Sentiment scores -> Positive: {pos}, Negative: {neg}, Neutral: {neu}, Compound: {compound}")
        store_entity_sentiment(conn, cursor, entity_id, pos, neg, neu, compound)

    logging.info("Sentiment analysis complete for all entities.")

# Main function to run the entire pipeline
def run_pipeline():
    logging.info("Starting sentiment analysis pipeline...")
    
    conn = connect_db()
    if conn is None:
        logging.error("Could not establish a database connection. Exiting.")
        return
    
    cursor = conn.cursor()

    # Populate surrounding sentences first
    populate_surrounding_sentences(cursor, conn)

    # Ensure the sentiment table exists
    create_sentiment_table(conn, cursor)
    
    # Process entities and analyze sentiment
    process_entity_sentiments(conn, cursor)

    # Close the database connection
    logging.info("Closing the database connection.")
    cursor.close()
    conn.close()
    logging.info("Database connection closed.")

# Execute the sentiment analysis pipeline
if __name__ == "__main__":
    run_pipeline()
