import numpy as np
import faiss
import psycopg2
import logging
import configparser
from tqdm import tqdm

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

# Function to fetch articles with embeddings
def fetch_articles_with_embeddings(cursor, batch_size=100):
    offset = 0
    while True:
        cursor.execute("SELECT article_id, embedding_vector_array FROM articles WHERE embedding_vector_array IS NOT NULL LIMIT %s OFFSET %s", (batch_size, offset))
        articles = cursor.fetchall()
        if not articles:
            break
        yield articles
        offset += batch_size

# Function to build and store FAISS index
def build_faiss_index(cursor, conn, index, batch_size=100):
    offset = 0
    embeddings = []
    ids = []

    try:
        # Fetch articles in batches
        for articles in fetch_articles_with_embeddings(cursor, batch_size):
            for article_id, embedding_array in articles:
                try:
                    # Convert PostgreSQL array to NumPy array
                    embedding = np.array(embedding_array, dtype=np.float32)
                    embeddings.append(embedding)
                    ids.append(article_id)
                except Exception as e:
                    logging.error(f"[ERROR] Error processing embedding for article_id {article_id}: {e}")
                    continue

        # Convert to numpy array
        embeddings_np = np.array(embeddings).astype('float32')

        if embeddings_np.shape[0] > 0:
            logging.info(f"Embedding shape: {embeddings_np.shape}")
            assert embeddings_np.shape[1] == index.d, f"Expected {index.d} dimensions, got {embeddings_np.shape[1]}"

            # Add the embeddings to FAISS index
            index.add(embeddings_np)
            logging.info(f"FAISS index built with {len(embeddings_np)} embeddings.")

            # Optionally, store the index on disk
            faiss.write_index(index, "faiss_index.index")
            logging.info("FAISS index saved to disk.")

            # Store the embeddings in the faiss_index table as BYTEA and update articles table
            for article_id, embedding in zip(ids, embeddings):
                try:
                    # Convert embedding to byte array
                    embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

                    # Insert into faiss_index table
                    cursor.execute("""
                        INSERT INTO faiss_index (article_id, faiss_vector)
                        VALUES (%s, %s)
                        ON CONFLICT (article_id) DO NOTHING;  -- Prevent duplicates
                    """, (article_id, psycopg2.Binary(embedding_bytes)))

                except Exception as e:
                    logging.error(f"[ERROR] Error inserting into faiss_index for article_id {article_id}: {e}")
                    conn.rollback()  # Rollback in case of error
                else:
                    conn.commit()  # Commit after successful update
        else:
            logging.error("No valid embeddings processed.")
    except Exception as e:
        logging.error(f"[ERROR] Error building FAISS index: {e}")

# Main function to run the FAISS pipeline
def run_faiss_pipeline():
    conn = connect_db()
    if conn is None:
        return

    cursor = conn.cursor()

    # Initialize FAISS index (dimension = 768 in your case)
    d = 768  # Ensure this matches your embedding size
    index = faiss.IndexFlatL2(d)

    # Build the FAISS index
    build_faiss_index(cursor, conn, index)

    # Close the connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_faiss_pipeline()
