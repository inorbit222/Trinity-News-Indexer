import psycopg2
import nltk
from nltk.corpus import stopwords
from gensim import corpora
from gensim.models.ldamodel import LdaModel

# Ensure stopwords are downloaded
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

# Database connection function
def connect_db():
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="Trinity Journal",
            user="postgres",
            password="skagen22",
            port="5432"
        )
        print("[INFO] Database connection successful.")
        return conn
    except psycopg2.Error as e:
        print(f"[ERROR] Error connecting to database: {e}")
        return None

    # Step 3: Fetch articles from the database
def fetch_articles_for_lda(cursor):
    print("[INFO] Fetching articles from the database...")
    cursor.execute("SELECT article_id, content FROM articles")
    articles = cursor.fetchall()
    print(f"[INFO] Retrieved {len(articles)} articles.")
    return articles


# Step 4: Preprocess the articles
def preprocess_text(text):
    tokens = [word.lower() for word in text.split() if word.isalpha() and word.lower() not in stop_words]
    return tokens

def preprocess_articles(cursor):
    articles = fetch_articles_for_lda(cursor)
    print("[INFO] Preprocessing articles...")
    processed_texts = [(article_id, preprocess_text(content)) for article_id, content in articles]
    print(f"[INFO] Preprocessed {len(processed_texts)} articles.")
    return processed_texts

# Step 5: Create dictionary and corpus for LDA
def create_dictionary_and_corpus(processed_texts):
    print("[INFO] Creating dictionary and corpus for LDA...")
    dictionary = corpora.Dictionary([text for _, text in processed_texts])
    dictionary.filter_extremes(no_below=5, no_above=0.5)
    corpus = [dictionary.doc2bow(text) for _, text in processed_texts]
    print("[INFO] Dictionary and corpus created.")
    return dictionary, corpus

# Step 6: Train LDA Model
def train_lda_model(corpus, dictionary, num_topics=20):
    print(f"[INFO] Training LDA model with {num_topics} topics. This might take some time...")
    lda_model = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=15)
    print("[INFO] LDA model training complete.")
    return lda_model

# Step 7: Store LDA topics in PostgreSQL with conflict handling
def store_lda_topics(conn, cursor, lda_model, corpus, processed_texts):
    print("[INFO] Storing LDA topics in the database...")

    for i, doc in enumerate(corpus):
        article_id = processed_texts[i][0]
        topic_distribution = lda_model.get_document_topics(doc)

        for topic_id, weight in topic_distribution:
            cursor.execute("""
                INSERT INTO topics (article_id, topic_id, topic_weight)
                VALUES (%s, %s, %s)
                ON CONFLICT (article_id, topic_id)
                DO UPDATE SET topic_weight = EXCLUDED.topic_weight;
            """, (article_id, topic_id, float(weight)))

    conn.commit()
    print("[INFO] LDA topics have been successfully stored in the database.")

# Main function to run the LDA pipeline
def run_lda_pipeline():
    print("[INFO] Starting the LDA pipeline...")

    conn = connect_db()
    if conn:
        cursor = conn.cursor()

        # Preprocess articles for LDA
        processed_texts = preprocess_articles(cursor)

        # Create dictionary and corpus
        dictionary, corpus = create_dictionary_and_corpus(processed_texts)

        # Train LDA model
        lda_model = train_lda_model(corpus, dictionary, num_topics=10)

        # Store topics in PostgreSQL (with conflict handling)
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
