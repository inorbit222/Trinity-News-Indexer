import psycopg2
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from gensim import corpora
from gensim.models import Phrases
from gensim.models.ldamodel import LdaModel
import configparser
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Download necessary NLTK resources
nltk.download('stopwords')
nltk.download('wordnet')
nltk.download('omw-1.4')

# Stop words and lemmatizer setup
stop_words = set(stopwords.words('english'))
lemmatizer = WordNetLemmatizer()

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')

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

# Fetch articles from the database
def fetch_articles(cursor, batch_size=100, offset=0):
    cursor.execute("SELECT article_id, content FROM articles LIMIT %s OFFSET %s", (batch_size, offset))
    return cursor.fetchall()

# Preprocess text: tokenize, remove stop words, and lemmatize
def preprocess_text(text):
    tokens = [lemmatizer.lemmatize(word.lower()) for word in text.split() if word.isalpha() and word.lower() not in stop_words]
    return tokens

# Preprocess all articles for LDA
def preprocess_articles(cursor):
    offset = 0
    batch_size = 100  # Batch size for fetching articles
    processed_texts = []

    while True:
        articles = fetch_articles(cursor, batch_size, offset)
        if not articles:
            break  # Stop when no more articles are fetched

        for article_id, content in articles:
            tokens = preprocess_text(content)
            processed_texts.append((article_id, tokens))

        offset += batch_size
        logging.info(f"[INFO] Preprocessed {offset} articles.")

    return processed_texts

# Create bigrams for the corpus
def create_bigrams(processed_texts):
    logging.info("[INFO] Detecting bigrams in the corpus...")
    
    # Collect the tokenized texts
    tokenized_texts = [text for _, text in processed_texts]
    
    # Detect bigrams in the tokenized texts
    bigram_model = Phrases(tokenized_texts, min_count=5, threshold=100)  # Adjust thresholds as needed
    bigram_phraser = bigram_model.freeze()
    
    # Add bigrams to tokenized texts
    bigram_texts = [bigram_phraser[text] for text in tokenized_texts]
    
    # Replace the original tokenized texts with the ones including bigrams
    processed_texts = [(processed_texts[i][0], bigram_texts[i]) for i in range(len(processed_texts))]
    
    logging.info("[INFO] Bigrams detection complete.")
    return processed_texts

# Create dictionary and corpus for LDA
def create_dictionary_and_corpus(processed_texts):
    logging.info("[INFO] Creating dictionary and corpus for LDA...")
    dictionary = corpora.Dictionary([text for _, text in processed_texts])
    dictionary.filter_extremes(no_below=5, no_above=0.5)
    corpus = [dictionary.doc2bow(text) for _, text in processed_texts]
    logging.info("[INFO] Dictionary and corpus created.")
    return dictionary, corpus

# Train LDA Model
def train_lda_model(corpus, dictionary, num_topics=20, passes=15):
    logging.info(f"[INFO] Training LDA model with {num_topics} topics...")
    lda_model = LdaModel(corpus, num_topics=num_topics, id2word=dictionary, passes=passes)
    logging.info("[INFO] LDA model training complete.")
    return lda_model

# Store LDA topics and article-topic relationships in the database
def store_lda_topics(conn, cursor, lda_model, corpus, processed_texts):
    try:
        logging.info("[INFO] Storing topics in the database...")

        # Insert topics into the `topics` table
        for topic_id, topic_terms in lda_model.show_topics(formatted=False):
            topic_words = " ".join([word for word, prob in topic_terms])

            # Truncate the topic name to 100 characters to fit the database constraint
            truncated_topic_words = topic_words[:100]  # Truncate to 100 characters

            cursor.execute("""
                INSERT INTO topics (topic_id, topic_name)
                VALUES (%s, %s)
                ON CONFLICT (topic_id) DO NOTHING;
            """, (topic_id, truncated_topic_words))

        logging.info("[INFO] Topics stored successfully.")

        # Insert relationships into `article_topics`
        logging.info("[INFO] Storing article-topic relationships...")
        for i, bow in enumerate(corpus):
            article_id = processed_texts[i][0]  # Extract the article_id from processed_texts

            # For each topic related to the article, insert the relationship into article_topics
            for topic_id, score in lda_model.get_document_topics(bow):
                try:
                    score_float = float(score)  # Convert numpy.float32 to Python float
                    cursor.execute("""
                        INSERT INTO article_topics (article_id, topic_id, topic_weight)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (article_id, topic_id) DO NOTHING;  -- Prevent duplicates
                    """, (article_id, topic_id, score_float))
                except Exception as e:
                    logging.error(f"[ERROR] Failed to insert article-topic relationship for article_id {article_id}, topic_id {topic_id}: {e}")

        conn.commit()  # Commit the changes after all inserts are successful
        logging.info("[INFO] Article-topic relationships stored successfully.")

    except psycopg2.Error as e:
        logging.error(f"[ERROR] Failed to store topics or article relationships: {e}")
        conn.rollback()  # Rollback if any critical error occurs



# Main function to run the LDA pipeline
def run_lda_pipeline(num_topics=10, batch_size=100):
    logging.info("[INFO] Starting the LDA pipeline...")

    conn = connect_db()
    if conn is None:
        return

    cursor = conn.cursor()

    # Preprocess articles
    processed_texts = preprocess_articles(cursor)

    # Create bigrams
    processed_texts = create_bigrams(processed_texts)

    # Create dictionary and corpus
    dictionary, corpus = create_dictionary_and_corpus(processed_texts)

    # Train LDA model
    lda_model = train_lda_model(corpus, dictionary, num_topics=num_topics)

    # Store topics and article-topic relationships in the database
    store_lda_topics(conn, cursor, lda_model, corpus, processed_texts)

    # Close the connection
    cursor.close()
    conn.close()
    logging.info("[INFO] LDA pipeline completed successfully.")

# Execute the LDA pipeline
if __name__ == "__main__":
    run_lda_pipeline(num_topics=10)
