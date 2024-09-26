import numpy as np
import faiss
import psycopg2

def build_faiss_index(cursor, conn, index):
    # Retrieve embeddings from the database
    cursor.execute("SELECT article_id, embedding_vector FROM articles")
    articles = cursor.fetchall()

    embeddings = []
    ids = []

    for article_id, embedding_str in articles:
        # Convert memoryview to bytes, then decode to string, and process it into a numpy array
        embedding_str = embedding_str.tobytes().decode('utf-8')
        embedding = np.fromstring(embedding_str.strip('[]'), sep=',')  # Convert string to numpy array

        embeddings.append(embedding)
        ids.append(article_id)

    # Convert to numpy array
    embeddings_np = np.array(embeddings).astype('float32')

    # Check the shape of the embeddings and compare to index dimension
    print(f"Embedding shape: {embeddings_np.shape}")
    assert embeddings_np.shape[1] == index.d, f"Expected {index.d} dimensions, got {embeddings_np.shape[1]}"

    # Add the embeddings to FAISS index
    index.add(embeddings_np)
    print(f"[INFO] FAISS index has been built with {len(embeddings_np)} embeddings.")

    # Optionally, store the index on disk
    faiss.write_index(index, "faiss_index.index")
    print("[INFO] FAISS index saved to disk.")

    # Commit any updates to the database
    conn.commit()

# Main function to run the FAISS pipeline
def run_faiss_pipeline():
    conn = psycopg2.connect(
        host="localhost",
        database="Trinity Journal",
        user="postgres",
        password="skagen22",
        port="5432"
    )
    cursor = conn.cursor()

    # Initialize FAISS index with the correct dimension (768 in your case)
    d = 768  # Change this to the correct dimension of your embeddings
    index = faiss.IndexFlatL2(d)

    # Build the FAISS index
    build_faiss_index(cursor, conn, index)

    # Close the connection
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_faiss_pipeline()

