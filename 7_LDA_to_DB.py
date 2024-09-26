import psycopg2
import nltk
from nltk.corpus import stopwords
from gensim import corpora
from gensim.models.ldamodel import LdaModel

# Ensure stopwords are downloaded
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# Step 1: Connect to PostgreSQL database
def connect_db():
    try:
        conn = psycopg2.connect(
            host="localhost",        # replace with your database host
            database="Trinity Journal", # replace with your database name
            user="postgres",         # replace with your username
            password="skagen22",      # replace with your password
            port="5432"
        )
        print("[INFO] Database connection successful.")
        return conn
    except psycopg2.Error as e:
        print(f"[ERROR] Error connecting to database: {e}")
        return None

# Step 2: Create necessary tables (if they don't exist)
# Step 2: Create necessary tables for LDA
def create_tables(conn, cursor):
    print("[INFO] Creating 'topics' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id SERIAL PRIMARY KEY,
        article_id INT REFERENCES articles(id),
        topic_id INT,
        topic_weight FLOAT
    );
    """)
    conn.commit()  # Commit the transaction after executing the SQL
    print("[INFO] 'topics' table is ready.")

def get_next_topic_id(cursor):
    cursor.execute("SELECT MAX(topic_id) FROM topics;")
    max_topic_id = cursor.fetchone()[0]
    if max_topic_id is None:
        return 1  # Start at 1 if no topics exist
    else:
        return max_topic_id + 1


# Step 3: Fetch articles from the database
def fetch_articles_for_lda(cursor):
    print("[INFO] Fetching articles from the database...")
    cursor.execute("SELECT article_id, content FROM articles")
    articles = cursor.fetchall()
    print(f"[INFO] Retrieved {len(articles)} articles.")
    return articles

# Step 4: Preprocess the articles
def preprocess_text(text):
    """
    Tokenizes text, lowercases words, and removes stopwords and non-alphabetic tokens.
    This function helps prepare the text for LDA.
    """
    tokens = [word.lower() for word in text.split() if word.isalpha() and word.lower() not in stop_words]
    return tokens

# Preprocess all articles
def preprocess_articles(cursor):
    """
    Preprocess all articles by fetching them from the database and applying text preprocessing.
    Returns a list of tuples where each tuple contains an article ID and its processed text.
    """
    articles = fetch_articles_for_lda(cursor)
    print("[INFO] Preprocessing articles...")
    processed_texts = [(article_id, preprocess_text(content)) for article_id, content in articles]
    print(f"[INFO] Preprocessed {len(processed_texts)} articles.")
    return processed_texts

# Step 5: Create dictionary and corpus for LDA
def create_dictionary_and_corpus(processed_texts):
    """
    Converts the processed texts into a dictionary and corpus for LDA.
    The dictionary maps unique words to IDs, and the corpus represents the frequency of words in each document.
    """
    print("[INFO] Creating dictionary and corpus for LDA...")

    # Create a dictionary representation of the documents.
    dictionary = corpora.Dictionary([text for _, text in processed_texts])

    # Filter out words that occur too frequently or too rarely
    dictionary.filter_extremes(no_below=5, no_above=0.5)

    # Create the bag-of-words format for each document
    corpus = [dictionary.doc2bow(text) for _, text in processed_texts]

    print("[INFO] Dictionary and corpus created.")
    return dictionary, corpus

# Step 6: Train LDA Model
def train_lda_model(corpus, dictionary, num_topics=20):
    """
    Train an LDA model with the provided corpus and dictionary.
    The LDA model will identify 'num_topics' number of topics from the documents.
    """
    print(f"[INFO] Training LDA model with {num_topics} topics. This might take some time...")

    # Train the LDA model with the corpus
    lda_model = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=15)

    print("[INFO] LDA model training complete.")
    return lda_model

# Step 7: Store LDA topics in PostgreSQL
def store_lda_topics(conn, cursor, lda_model, corpus, processed_texts):
    """
    Store the topic distribution for each document in the database.
    Each document will have a set of topics, and their corresponding weights will be saved.
    """
    print("[INFO] Storing LDA topics in the database...")

    for i, doc in enumerate(corpus):
        article_id = processed_texts[i][0]  # Get the article ID
        topic_distribution = lda_model.get_document_topics(doc)

        for topic_id, weight in topic_distribution:
            # Insert or update if conflict happens on (article_id, topic_id)
            cursor.execute("""
                INSERT INTO topics (article_id, topic_id, topic_weight)
                VALUES (%s, %s, %s)
                ON CONFLICT (article_id, topic_id) 
                DO UPDATE SET topic_weight = EXCLUDED.topic_weight;
            """, (article_id, topic_id, float(weight)))

    conn.commit()  # Use the connection to commit the transaction
    print("[INFO] LDA topics have been successfully stored in the database.")

   

# Step 8: Main function to run the LDA pipeline
# Main function to run the LDA pipeline
def run_lda_pipeline():
    print("[INFO] Starting the LDA pipeline...")

    # Connect to the database
# Main function to run the LDA pipeline
def run_lda_pipeline():
    print("[INFO] Starting the LDA pipeline...")

    # Connect to the database
    conn = connect_db()
    if conn:
        cursor = conn.cursor()

        # Create necessary tables
        create_tables(conn, cursor)  # Pass 'conn' and 'cursor' to the function

        # Preprocess articles for LDA
        processed_texts = preprocess_articles(cursor)

        # Create dictionary and corpus
        dictionary, corpus = create_dictionary_and_corpus(processed_texts)

        # Train LDA model
        lda_model = train_lda_model(corpus, dictionary, num_topics=10)

        # Store topics in PostgreSQL (Pass conn to store_lda_topics)
        store_lda_topics(conn, cursor, lda_model, corpus, processed_texts)

        # Close the connection
        cursor.close()
        conn.close()
        print("[INFO] LDA pipeline has successfully completed.")
    else:
        print("[ERROR] Could not establish a database connection.")


# Execute the LDA pipeline
if __name__ == "__main__":
    run_lda_pipeline()
