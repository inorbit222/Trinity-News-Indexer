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

# Fetch summaries from the database
def fetch_summaries(cursor, batch_size=100, offset=0):
    cursor.execute("SELECT article_id, summary FROM articles WHERE summary IS NOT NULL LIMIT %s OFFSET %s", (batch_size, offset))
    return cursor.fetchall()

# Preprocess text: tokenize, remove stop words, and lemmatize
def preprocess_text(text):
    tokens = [lemmatizer.lemmatize(word.lower()) for word in text.split() if word.isalpha() and word.lower() not in stop_words]
    return tokens

# Preprocess all summaries for LDA
def preprocess_summaries(cursor):
    offset = 0
    batch_size = 100  # Batch size for fetching summaries
    processed_texts = []

    while True:
        summaries = fetch_summaries(cursor, batch_size, offset)
        if not summaries:
            break  # Stop when no more summaries are fetched

        for article_id, summary in summaries:
            tokens = preprocess_text(summary)
            processed_texts.append((article_id, tokens))

        offset += batch_size
        logging.info(f"[INFO] Preprocessed {offset} summaries.")

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

# Store LDA topics into the summary_topics column in the articles table
def store_summary_lda_topics(conn, cursor, lda_model, corpus, processed_texts):
    try:
        logging.info("[INFO] Storing summary topics in the database...")

        for i, bow in enumerate(corpus):
            article_id = processed_texts[i][0]  # Extract the article_id from processed_texts

            # Get the most relevant topics for the summary
            topics = lda_model.get_document_topics(bow)

            # Convert the topic data into a string format for storing in the summary_topics column
            summary_topics_str = ", ".join([f"Topic {topic_id}: {score:.4f}" for topic_id, score in topics])

            # Update the summary_topics column for the corresponding article_id
            cursor.execute("""
                UPDATE articles
                SET summary_topics = %s
                WHERE article_id = %s;
            """, (summary_topics_str, article_id))

        conn.commit()  # Commit the changes after all updates are successful
        logging.info("[INFO] Summary topics stored successfully in the summary_topics column.")

    except psycopg2.Error as e:
        logging.error(f"[ERROR] Failed to store summary topics for article {article_id}: {e}")
        conn.rollback()  # Rollback if any critical error occurs




# Main function to run the LDA pipeline for summaries
def run_lda_pipeline_on_summaries(num_topics=10, batch_size=100):
    logging.info("[INFO] Starting the LDA pipeline on summaries...")

    conn = connect_db()
    if conn is None:
        return

    cursor = conn.cursor()

    # Preprocess summaries
    processed_texts = preprocess_summaries(cursor)

    # Create bigrams
    processed_texts = create_bigrams(processed_texts)

    # Create dictionary and corpus
    dictionary, corpus = create_dictionary_and_corpus(processed_texts)

    # Train LDA model
    lda_model = train_lda_model(corpus, dictionary, num_topics=num_topics)

    # Store topics and article-topic relationships in the database
    store_summary_lda_topics(conn, cursor, lda_model, corpus, processed_texts)

    # Close the connection
    cursor.close()
    conn.close()
    logging.info("[INFO] LDA pipeline on summaries completed successfully.")

# Execute the LDA pipeline on summaries
if __name__ == "__main__":
    run_lda_pipeline_on_summaries(num_topics=10)