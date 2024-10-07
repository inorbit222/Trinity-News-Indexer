from sentence_transformers import SentenceTransformer
import psycopg2
import numpy as np
import configparser
import torch

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')

# Access database settings from settings.ini
db_host = config['database']['host']
db_name = config['database']['database']
db_user = config['database']['user']
db_password = config['database']['password']
db_port = config['database']['port']

# Establish the database connection
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

# Initialize the sentence transformer model
model = SentenceTransformer('sentence-transformers/gtr-t5-large')

# Generator function to yield batches of articles
def article_batch_generator(cursor, batch_size=100):
    offset = 0
    while True:
        cursor.execute("""
            SELECT article_id, content FROM articles 
            WHERE embedding_vector IS NULL 
            ORDER BY article_id 
            LIMIT %s OFFSET %s
        """, (batch_size, offset))
        results = cursor.fetchall()
        if not results:
            break
        yield results
        offset += batch_size

# Embedding articles in batches and storing in two formats
def process_articles_in_batches(batch_size=100):
    conn = connect_db()
    if not conn:
        return

    cursor = conn.cursor()

    for batch in article_batch_generator(cursor, batch_size):
        articles = [article[1] for article in batch]
        article_ids = [article[0] for article in batch]

        # Embed the batch
        embeddings = model.encode(articles, convert_to_numpy=True)

        # Insert/update embeddings into the database
        for article_id, embedding_vector in zip(article_ids, embeddings):
            # 1. Store the embedding as a binary bytea format
            embedding_binary = embedding_vector.tobytes()

            # 2. Store the embedding as a NumPy array (PostgreSQL array format)
            embedding_array = embedding_vector.tolist()

            # Update the article row with the generated embeddings (binary and array)
            cursor.execute("""
                UPDATE articles 
                SET embedding_vector = %s, embedding_vector_array = %s 
                WHERE article_id = %s;
            """, (psycopg2.Binary(embedding_binary), embedding_array, article_id))

        conn.commit()

    cursor.close()
    conn.close()
    print("[INFO] Embeddings generated and stored successfully.")

# Call the function with the desired batch size
process_articles_in_batches(batch_size=100)
