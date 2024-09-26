import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
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

# Function to generate and store embeddings
def generate_and_store_embeddings():
    # Initialize the sentence transformer model
    model = SentenceTransformer('sentence-transformers/gtr-t5-large')
    
    # Connect to the database
    conn = connect_db()
    if conn is None:
        return

    with conn.cursor() as cur:
        # Fetch all articles that don't have embeddings yet
        cur.execute("SELECT article_id, content FROM articles WHERE embedding_vector_binary IS NULL;")
        articles = cur.fetchall()

        for article_id, content in articles:
            # Generate the embedding for the article content
            embedding_vector = model.encode(content, convert_to_numpy=True)

            # 1. Store the embedding as a binary bytea format (byte stream)
            embedding_binary = embedding_vector.tobytes()  # Convert numpy array to binary format (bytea)

            # 2. Store the embedding as a NumPy array (PostgreSQL array format)
            embedding_array = embedding_vector.tolist()  # Convert numpy array to list for PostgreSQL

            # Update the article row with the generated embeddings (binary and array)
            cur.execute("""
                UPDATE articles 
                SET embedding_vector_binary = %s, embedding_vector_array = %s 
                WHERE article_id = %s;
            """, (psycopg2.Binary(embedding_binary), embedding_array, article_id))

        conn.commit()

    conn.close()
    print("Embeddings generated and stored successfully.")

# Run the embedding generation process
generate_and_store_embeddings()
