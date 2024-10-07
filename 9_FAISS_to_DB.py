import numpy as np
import faiss
import psycopg2
import logging
import configparser

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def build_faiss_index(cursor, conn, index, batch_size=100):
    offset = 0
    embeddings = []
    ids = []

    try:
        # Get the total number of articles
        cursor.execute("SELECT COUNT(*) FROM articles WHERE embedding_vector_array IS NOT NULL")
        total_articles = cursor.fetchone()[0]
        logging.info(f"Total articles with embeddings found: {total_articles}")

        # Process embeddings in batches
        while offset < total_articles:
            cursor.execute("SELECT article_id, embedding_vector_array FROM articles WHERE embedding_vector_array IS NOT NULL LIMIT %s OFFSET %s", (batch_size, offset))
            articles = cursor.fetchall()

            for article_id, embedding_array in articles:
                try:
                    # Convert the PostgreSQL array to NumPy array
                    embedding = np.array(embedding_array, dtype=np.float32)

                    embeddings.append(embedding)
                    ids.append(article_id)
                except Exception as e:
                    logging.error(f"Error processing embedding for article_id {article_id}: {e}")
            
            offset += batch_size

        # Convert to numpy array
        embeddings_np = np.array(embeddings).astype('float32')

        # Check the shape of the embeddings and compare to index dimension
        if embeddings_np.shape[0] > 0:  # Only log if we have embeddings
            logging.info(f"Embedding shape: {embeddings_np.shape}")
            assert embeddings_np.shape[1] == index.d, f"Expected {index.d} dimensions, got {embeddings_np.shape[1]}"

            # Add the embeddings to FAISS index
            index.add(embeddings_np)
            logging.info(f"FAISS index has been built with {len(embeddings_np)} embeddings.")

            # Optionally, store the index on disk
            faiss.write_index(index, "faiss_index.index")
            logging.info("FAISS index saved to disk.")
        else:
            logging.error("No valid embeddings were processed.")

        # Commit any updates to the database
        conn.commit()

    except Exception as e:
        logging.error(f"Error building FAISS index: {e}")

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


# Main function to run the FAISS pipeline
def run_faiss_pipeline():
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        logging.info("[INFO] Database connection successful.")
        
        cursor = conn.cursor()

        # Initialize FAISS index with the correct dimension (768 in your case)
        d = 768  # Change this to the correct dimension of your embeddings
        index = faiss.IndexFlatL2(d)

        # Build the FAISS index
        build_faiss_index(cursor, conn, index)

        # Close the connection
        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        logging.error(f"[ERROR] Could not connect to the database: {e}")
    except Exception as e:
        logging.error(f"Error in FAISS pipeline: {e}")

if __name__ == "__main__":
    run_faiss_pipeline()
