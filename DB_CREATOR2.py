import configparser
import psycopg2

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


# Step 2: Create necessary tables for the project
def create_tables(cursor):
    commands = [
        """
        CREATE TABLE IF NOT EXISTS Newspapers (
            newspaper_id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            publication_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            toc TEXT,
            hyperlink TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Articles (
            article_id SERIAL PRIMARY KEY,
            newspaper_id INT REFERENCES Newspapers(newspaper_id),
            title VARCHAR(255),
            content TEXT,
            embedding_vector BYTEA,  -- Embeddings will be stored here
            embedding_vector_cube public.cube,  -- Cube type for vector storage
            embedding_vector_binary BYTEA,
            embedding_vector_array DOUBLE PRECISION[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Entities (
            entity_id SERIAL PRIMARY KEY,
            article_id INT REFERENCES Articles(article_id),
            entity_type VARCHAR(255),
            entity_value VARCHAR(255),
            start_pos INT,
            end_pos INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Topics (
            topic_id SERIAL PRIMARY KEY,
            topic_name VARCHAR(100) NOT NULL,
            description TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Article_Topics (
            article_id INT REFERENCES Articles(article_id),
            topic_id INT REFERENCES Topics(topic_id),
            topic_weight REAL,
            PRIMARY KEY (article_id, topic_id)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS Geocoded_Locations (
            entity_id INT PRIMARY KEY REFERENCES Entities(entity_id),
            latitude NUMERIC(9, 6),
            longitude NUMERIC(9, 6),
            geocoding_source VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS entity_sentiments (
            id SERIAL PRIMARY KEY,
            entity_id INT REFERENCES Entities(entity_id),
            sentiment_pos FLOAT,    -- Positive sentiment score (0 to 1)
            sentiment_neg FLOAT,    -- Negative sentiment score (0 to 1)
            sentiment_neu FLOAT,    -- Neutral sentiment score (0 to 1)
            sentiment_compound FLOAT -- Compound sentiment score (-1 to 1)
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS faiss_index (
            index_id SERIAL PRIMARY KEY,
            article_id INT REFERENCES Articles(article_id),
            faiss_vector BYTEA
        );
        """
    ]

    # Execute each SQL command
    for command in commands:
        cursor.execute(command)

    print("[INFO] All tables created or confirmed to exist.")


# Step 3: Run schema creation
def run_schema_creation():
    print("[INFO] Starting the schema creation process...")

    # Connect to the database
    conn = connect_db()
    if conn is None:
        print("[ERROR] Could not establish a database connection. Exiting.")
        return
    
    cursor = conn.cursor()

    # Enable the cube extension (if not already installed)
    cursor.execute("CREATE EXTENSION IF NOT EXISTS cube;")

    # Create all tables
    create_tables(cursor)

    # Commit the changes and close the connection
    conn.commit()
    cursor.close()
    conn.close()
    print("[INFO] Database schema creation complete.")


# Main execution
if __name__ == "__main__":
    run_schema_creation()
