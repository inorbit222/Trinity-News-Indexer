import psycopg2
import faiss
import numpy as np
import openai
import configparser
import json
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import re

# Load settings from the settings.ini file
config = configparser.ConfigParser()
config.read('settings.ini')

# Load OpenAI API Key from settings.ini
openai.api_key = config['openai']['api_key']

# Database credentials from settings.ini
db_host = config['database']['host']
db_name = config['database']['database']
db_user = config['database']['user']
db_password = config['database']['password']
db_port = config['database']['port']

# Step 1: Connect to PostgreSQL database
def connect_db():
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=db_port
        )
        print("[INFO] Connected to the database.")
        return conn
    except psycopg2.Error as e:
        print(f"[ERROR] Could not connect to the database: {e}")
        return None

# Load a sentence transformer model
def load_embedding_model():
    model = SentenceTransformer('sentence-transformers/gtr-t5-large')
    return model

# Generate an embedding for the user's input
def generate_user_embedding(user_input):
    model = load_embedding_model()
    return model.encode(user_input)

# Load a pretrained NER model
def load_ner_model():
    return pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

# Extract entities using NER
def extract_entity(user_input):
    nlp = load_ner_model()
    entities = nlp(user_input)
    if entities:
        return entities[0]['word'], entities[0]['entity']
    return None, None

# Fetch FAISS vectors from the database
def get_faiss_vectors_from_db(cursor):
    cursor.execute("SELECT article_id, faiss_vector FROM faiss_index")
    rows = cursor.fetchall()

    article_ids = []
    vectors = []
    for row in rows:
        article_id = row[0]
        vector_str = row[1]
        vector = np.fromstring(vector_str.strip('[]'), sep=',')
        article_ids.append(article_id)
        vectors.append(vector)
    
    return np.array(article_ids), np.array(vectors).astype('float32')

# Build and search FAISS index
def search_faiss_index(user_embedding, cursor):
    article_ids, vectors = get_faiss_vectors_from_db(cursor)
    
    if len(vectors) == 0:
        print("[ERROR] No FAISS vectors retrieved from the database.")
        return []
    
    dimension = vectors.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)
    
    D, I = index.search(np.array([user_embedding]).astype('float32'), 5)
    return [article_ids[idx] for idx in I[0]]

# Search entities from the database
def search_by_entity(cursor, entity_value, entity_type):
    query = """
    SELECT article_id, entity_value, entity_type
    FROM entities
    WHERE entity_value = %s AND entity_type = %s;
    """
    cursor.execute(query, (entity_value, entity_type))
    return cursor.fetchall()

# Search geospatial locations from the database
def search_nearby_locations(cursor, lat, lon, radius_km=50):
    query = f"""
    SELECT article_id, location_name, latitude, longitude
    FROM geocoded_locations
    WHERE earth_distance(ll_to_earth(latitude, longitude), ll_to_earth({lat}, {lon})) < {radius_km * 1000};
    """
    cursor.execute(query)
    return cursor.fetchall()

import numpy as np

# Convert numpy array to a PostgreSQL-compatible string
def numpy_array_to_postgres_vector(embedding):
    # Convert the NumPy array to a list and then to a string in the form of "{0.1, 0.2, 0.3,...}"
    return '{' + ','.join(map(str, embedding)) + '}'

# Find similar sentences based on the user's embedding
def find_similar_sentences(cursor, user_embedding):
    # Convert NumPy array to a PostgreSQL-compatible format
    user_embedding_str = numpy_array_to_postgres_vector(user_embedding)

    query = """
    SELECT article_id, title, content
    FROM articles
    ORDER BY cube_distance(embedding_vector, %s) ASC
    LIMIT 5;
    """
    
    # Execute query and pass the embedding string as a parameter
    cursor.execute(query, (user_embedding_str,))
    return cursor.fetchall()


# Search sentiment scores for entities
def search_by_sentiment(cursor, entity_id, min_pos=None, min_neg=None):
    query = "SELECT * FROM entity_sentiments WHERE entity_id = %s"
    conditions = []
    if min_pos is not None:
        conditions.append(f"sentiment_pos >= {min_pos}")
    if min_neg is not None:
        conditions.append(f"sentiment_neg >= {min_neg}")
    query += " AND ".join(conditions)
    cursor.execute(query, (entity_id,))
    return cursor.fetchall()


# Query all indices and return results
def query_all_indices(cursor, user_input):
    # Generate user embedding
    user_embedding = generate_user_embedding(user_input)
    faiss_results = search_faiss_index(user_embedding, cursor)

    # Extract entities and perform NER search
    entity_value, entity_type = extract_entity(user_input)
    if entity_value and entity_type:
        ner_results = search_by_entity(cursor, entity_value, entity_type)
    else:
        ner_results = []

    # Extract lat/lon from the database using the location name
    lat, lon = extract_location(user_input, cursor)  # Now uses the database
    geospatial_results = search_nearby_locations(cursor, lat, lon) if lat and lon else []

    # Find sentence similarity results
    sentence_results = find_similar_sentences(cursor, user_embedding)

    # Sentiment search based on entity ID
    entity_id = get_entity_id_from_input(user_input)  # Assuming this function is implemented
    sentiment_results = search_by_sentiment(cursor, entity_id)

    # Return all results in a structured format
    return {
        "faiss_results": faiss_results,
        "ner_results": ner_results,
        "geospatial_results": geospatial_results,
        "sentence_results": sentence_results,
        "sentiment_results": sentiment_results
    }



# Function to extract latitude and longitude from the database
def extract_location_from_db(cursor, location_name):
    try:
        # Query to retrieve latitude and longitude based on the location name
        query = """
        SELECT latitude, longitude
        FROM geocoded_locations
        WHERE location_name = %s
        LIMIT 1;
        """
        cursor.execute(query, (location_name,))
        result = cursor.fetchone()
        
        if result:
            lat, lon = result
            return lat, lon
        else:
            print(f"[INFO] No geocoded location found for '{location_name}'")
            return None, None
    except Exception as e:
        print(f"[ERROR] Failed to retrieve location from the database: {e}")
        return None, None

# Updated extract_location function
def extract_location(user_input, cursor):
    entity_value, entity_type = extract_entity(user_input)  # Use the NER function to extract entities
    if entity_type == "LOC":  # If a location is detected
        return extract_location_from_db(cursor, entity_value)  # Retrieve lat/lon from the database
    return None, None



    lat, lon = extract_location(user_input)  # Assuming extract_location function
    geospatial_results = search_nearby_locations(cursor, lat, lon) if lat and lon else []

    sentence_results = find_similar_sentences(cursor, user_embedding)
    entity_id = get_entity_id_from_input(user_input)  # Assuming get_entity_id_from_input function
    sentiment_results = search_by_sentiment(cursor, entity_id)

    return {
        "faiss_results": faiss_results,
        "ner_results": ner_results,
        "geospatial_results": geospatial_results,
        "sentence_results": sentence_results,
        "sentiment_results": sentiment_results
    }

# Generate OpenAI response from standardized results
def generate_openai_response(user_input, standardized_results):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"User asked: {user_input}. Here are the results from various database indices: {standardized_results}. Generate a relevant answer."}
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=500
    )
    return response['choices'][0]['message']['content']

# Main conversation loop
def run_conversation():
    conn = connect_db()
    if conn is None:
        return
    
    cursor = conn.cursor()
    user_input = input("Ask your question: ")

    results = query_all_indices(cursor, user_input)
    standardized_results = create_standardized_output(results)
    
    response = generate_openai_response(user_input, standardized_results)
    print(response)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_conversation()
