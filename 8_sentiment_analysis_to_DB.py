import logging
import psycopg2
from transformers import pipeline
import configparser
import torch

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU

# Load the sentiment analysis pipeline from Hugging Face
sentiment_model = pipeline("sentiment-analysis", device=device)

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
print(f"Using device: {'GPU' if device == 0 else 'CPU'}")

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')
db_host = config['database']['host']
db_name = config['database']['database']
db_user = config['database']['user']
db_password = config['database']['password']
db_port = config['database']['port']

# Database connection
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

# Fetch articles from the database
def fetch_articles(cursor, batch_size=100):
    logging.info("Fetching articles from the 'articles' table in batches...")
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = cursor.fetchone()[0]
    logging.info(f"Total articles found: {total_articles}")

    offset = 0
    while offset < total_articles:
        cursor.execute("SELECT article_id, summary FROM articles LIMIT %s OFFSET %s", (batch_size, offset))
        articles = cursor.fetchall()
        logging.info(f"Fetched {len(articles)} articles in batch.")
        yield articles
        offset += batch_size

# Batch process sentiment analysis
def process_sentiment_analysis(cursor, conn, batch_size=100):
    for articles_batch in fetch_articles(cursor, batch_size):
        entity_data = []
        for article_id, content in articles_batch:
            try:
                logging.info(f"Processing sentiment for article ID {article_id}...")

                # Apply sentiment analysis to the article content
                sentiments = sentiment_model(content[:512])  # Limiting the content length for processing efficiency
                logging.info(f"Sentiment results: {sentiments}")

                for sentiment in sentiments:
                    sentiment_score = sentiment['score']
                    sentiment_label = sentiment['label']
                    if sentiment_label == 'POSITIVE':
                        sentiment_pos, sentiment_neg, sentiment_neu = sentiment_score, 0.0, 0.0
                    elif sentiment_label == 'NEGATIVE':
                        sentiment_pos, sentiment_neg, sentiment_neu = 0.0, sentiment_score, 0.0
                    else:
                        sentiment_pos, sentiment_neg, sentiment_neu = 0.0, 0.0, sentiment_score
                    
                    entity_data.append((article_id, sentiment_pos, sentiment_neg, sentiment_neu, sentiment_score))

            except Exception as e:
                logging.error(f"Error processing sentiment for article ID {article_id}: {e}")

        # Insert sentiment results in batch to improve performance
        insert_sentiments(cursor, entity_data)
        conn.commit()

# Insert sentiments into the database
def insert_sentiments(cursor, entity_data):
    logging.info(f"Inserting sentiment results for {len(entity_data)} articles...")
    query = """
        INSERT INTO entity_sentiments (entity_id, sentiment_pos, sentiment_neg, sentiment_neu, sentiment_compound)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (entity_id) DO NOTHING;
    """
    try:
        cursor.executemany(query, entity_data)
        logging.info("Sentiment results inserted successfully.")
    except psycopg2.Error as e:
        logging.error(f"Error inserting sentiment results: {e}")

# Main function to run the sentiment analysis pipeline
def run_sentiment_analysis_pipeline(batch_size=100):
    logging.info("Starting sentiment analysis pipeline...")

    conn = connect_db()
    if conn is None:
        return

    cursor = conn.cursor()

    # Process articles in batches and store sentiment results
    process_sentiment_analysis(cursor, conn, batch_size=batch_size)

    # Close the connection after everything is done
    cursor.close()
    conn.close()
    logging.info("Sentiment analysis pipeline completed successfully.")

# Execute the sentiment analysis pipeline
if __name__ == "__main__":
    run_sentiment_analysis_pipeline(batch_size=100)
