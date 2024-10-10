import psycopg2
import geopy
from geopy.geocoders import Nominatim
import configparser
import logging
import time
import re  # For cleaning non-text characters

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load settings from the ini file
config = configparser.ConfigParser()
config.read('settings.ini')

# Access database settings from settings.ini
db_host = config['database']['host']
db_name = config['database']['database']
db_user = config['database']['user']
db_password = config['database']['password']
db_port = config['database']['port']

# Dictionary of common multi-word place names
known_place_names = {
    "san francisco": "San Francisco",
    "new york": "New York",
    "atlantic states": "Atlantic States",
    "los angeles": "Los Angeles",
    # Add more as needed
}

# Function to clean and combine OCR outputs
def clean_place_name(entity_value):
    # Convert to lowercase
    entity_value = entity_value.lower()

    # Remove non-alphabetic characters (retain only letters and spaces)
    entity_value = re.sub(r'[^a-z\s]', '', entity_value)

    # Normalize spaces (remove extra spaces)
    entity_value = re.sub(r'\s+', ' ', entity_value).strip()

    # Check if the entity matches any known place names
    for place in known_place_names:
        if place in entity_value:
            return known_place_names[place]  # Return the correctly combined place name

    return entity_value.title()  # Convert back to title case for geocoding

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
        logging.info("Database connection successful.")
        return conn
    except psycopg2.Error as e:
        logging.error(f"Could not connect to the database: {e}")
        return None

# Step 2: Fetch entities for geocoding
def fetch_entities(cursor, batch_size=100, offset=0):
    cursor.execute("SELECT entity_id, entity_value FROM entities WHERE entity_type = 'LOC' LIMIT %s OFFSET %s;", (batch_size, offset))
    entities = cursor.fetchall()
    logging.info(f"Fetched {len(entities)} entities for geocoding.")
    return entities

# Step 3: Geocode entity locations with caching
def geocode_entity(entity_value, geocode_cache, geolocator):
    # First clean up the place name
    cleaned_entity = clean_place_name(entity_value)

    # Check if we already geocoded this entity value
    if cleaned_entity in geocode_cache:
        logging.info(f"Cache hit for {cleaned_entity}")
        return geocode_cache[cleaned_entity]

    # Perform geocoding if not already cached
    logging.info(f"Geocoding {cleaned_entity}")
    try:
        location = geolocator.geocode(cleaned_entity, timeout=10)
    except Exception as e:
        logging.error(f"Error during geocoding {cleaned_entity}: {e}")
        return None, None, None

    if location:
        result = (location.latitude, location.longitude, location.raw.get('display_name'))
        logging.info(f"Found location for {cleaned_entity}: {result}")
    else:
        result = (None, None, None)
        logging.warning(f"No geocoding result for {cleaned_entity}")

    # Cache the result to avoid redundant geocoding
    geocode_cache[cleaned_entity] = result
    return result

# Step 4: Store geocoded locations in the database
def store_geocoded_location(cursor, entity_id, latitude, longitude, source):
    try:
        cursor.execute("""
            INSERT INTO geocoded_locations (entity_id, latitude, longitude, geocoding_source)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (entity_id) DO NOTHING;  -- Avoid inserting duplicates
        """, (entity_id, latitude, longitude, source))
    except Exception as e:
        logging.error(f"Error inserting geocoded location for entity_id {entity_id}: {e}")

# Step 5: Main function to run geocoding and store results with batching and error handling
def run_geo_pipeline(batch_size=100):
    logging.info("Starting geocoding process...")
    
    conn = connect_db()
    if conn is None:
        logging.error("Failed to connect to the database. Exiting.")
        return
    cursor = conn.cursor()

    # Initialize geolocator with a longer timeout
    geolocator = Nominatim(user_agent="geo_coder", timeout=10)
    geocode_cache = {}

    offset = 0
    while True:
        # Fetch entities in batches
        entities = fetch_entities(cursor, batch_size=batch_size, offset=offset)
        if not entities:
            break

        for entity_id, entity_value in entities:
            logging.info(f"Processing entity ID {entity_id} with value '{entity_value}'")
            latitude, longitude, source = geocode_entity(entity_value, geocode_cache, geolocator)
            
            if latitude and longitude:
                store_geocoded_location(cursor, entity_id, latitude, longitude, source)
                logging.info(f"Geocoded: {entity_value} -> {latitude}, {longitude}")
            else:
                logging.warning(f"Failed to geocode: {entity_value}")
            
            # Introduce rate limiting: 1 second delay between requests
            time.sleep(1)

        # Commit after each batch
        conn.commit()
        offset += batch_size

    cursor.close()
    conn.close()
    logging.info("Geocoding pipeline completed.")

if __name__ == "__main__":
    run_geo_pipeline(batch_size=100)
