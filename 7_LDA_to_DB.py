import psycopg2
import nltk
from nltk.corpus import stopwords
from gensim import corpora
from gensim.models.ldamodel import LdaModel
import configparser
import torch

# Check if CUDA is available and set device
device = 0 if torch.cuda.is_available() else -1  # 0 for GPU, -1 for CPU

# Ensure stopwords are downloaded
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))

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
    # Step 1: Insert topics into the `topics` table
    print("[INFO] Storing topics in the topics table...")
    for topic_id, topic_terms in lda_model.show_topics(formatted=False):
        topic_words = " ".join([word for word, prob in topic_terms])
        
        # Insert the topic into the topics table, avoiding duplicates
        cursor.execute("""
            INSERT INTO topics (topic_id, topic_name)
            VALUES (%s, %s)
            ON CONFLICT (topic_id) DO NOTHING;  -- Avoid inserting duplicate topics
        """, (topic_id, topic_words))
    
    # Commit after inserting all topics
    conn.commit()

    # Step 2: Insert relationships into `article_topics`
    print("[INFO] Storing article-topic relationships...")
    for i, bow in enumerate(corpus):
        article_id = processed_texts[i][0]  # Extract the article_id from processed_texts

        # For each topic related to the article, insert the relationship into article_topics
        for topic_id, score in lda_model.get_document_topics(bow):
            cursor.execute("""
                INSERT INTO article_topics (article_id, topic_id)
                VALUES (%s, %s);
            """, (article_id, topic_id))
    
    conn.commit()
    print("[INFO] LDA topics and relationships have been successfully stored in the database.")



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
