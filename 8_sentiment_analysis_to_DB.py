import psycopg2
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

# Initialize the VADER sentiment analyzer
analyzer = SentimentIntensityAnalyzer()

# Step 1: Connect to your PostgreSQL database
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

# Step 2: Create table for storing entity-level sentiment data
def create_sentiment_table(conn, cursor):
    print("[INFO] Creating 'entity_sentiments' table if it doesn't exist...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS entity_sentiments (
        id SERIAL PRIMARY KEY,
        entity_id INT REFERENCES entities(id),
        sentiment_pos FLOAT,    -- Positive sentiment score (0 to 1)
        sentiment_neg FLOAT,    -- Negative sentiment score (0 to 1)
        sentiment_neu FLOAT,    -- Neutral sentiment score (0 to 1)
        sentiment_compound FLOAT -- Compound sentiment score (-1 to 1)
    );
    """)
    conn.commit()
    print("[INFO] 'entity_sentiments' table is ready.")

# Step 3: Fetch entities and corresponding article content to populate surrounding sentences
def fetch_entities_with_articles(cursor):
    cursor.execute("""
        SELECT e.id, e.entity_value, a.content
        FROM entities e
        JOIN articles a ON e.article_id = a.article_id
    """)
    entities = cursor.fetchall()
    print(f"[INFO] Retrieved {len(entities)} entities with corresponding article content.")
    return entities

# Step 4: Function to extract the surrounding sentence for an entity within the article content
def extract_surrounding_sentence(entity, content):
    pattern = rf"([^.]*?{re.escape(entity)}[^.]*\.)"
    match = re.search(pattern, content)
    if match:
        return match.group(0)  # Return the sentence containing the entity
    return None  # Return None if no match is found

# Step 5: Update the surrounding_sentence field in the database
def update_surrounding_sentence(cursor, entity_id, surrounding_sentence):
    cursor.execute("""
        UPDATE entities
        SET surrounding_sentence = %s
        WHERE id = %s
    """, (surrounding_sentence, entity_id))

# Step 6: Populate surrounding sentences for entities
def populate_surrounding_sentences(cursor):
    entities = fetch_entities_with_articles(cursor)
    
    for entity_id, entity_value, article_content in entities:
        surrounding_sentence = extract_surrounding_sentence(entity_value, article_content)
        
        if surrounding_sentence:
            update_surrounding_sentence(cursor, entity_id, surrounding_sentence)
            print(f"[INFO] Updated entity ID {entity_id} with surrounding sentence.")
        else:
            print(f"[WARNING] No surrounding sentence found for entity ID {entity_id}.")

# Step 7: Fetch entities for sentiment analysis
def fetch_entities_for_sentiment(cursor):
    cursor.execute("SELECT id, entity_value, surrounding_sentence FROM entities WHERE surrounding_sentence IS NOT NULL")
    entities = cursor.fetchall()
    print(f"[INFO] Retrieved {len(entities)} entities with surrounding sentences for sentiment analysis.")
    return entities

# Step 8: Analyze sentiment for each entity using VADER
def analyze_entity_sentiment(entity_text):
    sentiment_scores = analyzer.polarity_scores(entity_text)
    return sentiment_scores['pos'], sentiment_scores['neg'], sentiment_scores['neu'], sentiment_scores['compound']

# Step 9: Store sentiment data in PostgreSQL
def store_entity_sentiment(conn, cursor, entity_id, pos, neg, neu, compound):
    cursor.execute("""
        INSERT INTO entity_sentiments (entity_id, sentiment_pos, sentiment_neg, sentiment_neu, sentiment_compound)
        VALUES (%s, %s, %s, %s, %s)
    """, (entity_id, pos, neg, neu, compound))
    conn.commit()

# Step 10: Process entities for sentiment analysis and store results
def process_entity_sentiments(conn, cursor):
    entities = fetch_entities_for_sentiment(cursor)

    for entity_id, entity_value, surrounding_sentence in entities:
        print(f"[INFO] Analyzing sentiment for entity '{entity_value}' (ID: {entity_id})...")
        pos, neg, neu, compound = analyze_entity_sentiment(surrounding_sentence)
        print(f"[INFO] Sentiment scores -> Positive: {pos}, Negative: {neg}, Neutral: {neu}, Compound: {compound}")
        store_entity_sentiment(conn, cursor, entity_id, pos, neg, neu, compound)

    print("[INFO] Sentiment analysis complete for all entities.")

# Main function to run the entire pipeline
def run_pipeline():
    print("[INFO] Starting sentiment analysis pipeline...")
    
    # Connect to the database
    conn = connect_db()
    if conn is None:
        print("[ERROR] Could not establish a database connection. Exiting.")
        return
    
    cursor = conn.cursor()

    # Populate surrounding sentences first
    populate_surrounding_sentences(cursor)

    # Ensure the sentiment table exists
    create_sentiment_table(conn, cursor)
    
    # Process entities and analyze sentiment
    process_entity_sentiments(conn, cursor)

    # Close the database connection
    print("[INFO] Closing the database connection.")
    cursor.close()
    conn.close()
    print("[INFO] Database connection closed.")

# Execute the sentiment analysis pipeline
if __name__ == "__main__":
    run_pipeline()
