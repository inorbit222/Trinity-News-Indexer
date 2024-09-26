#GEO_to_DB
import psycopg2
import geopy
from geopy.geocoders import Nominatim

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

# Step 2: Fetch entities for geocoding
def fetch_entities(cursor):
    cursor.execute("SELECT entity_id, entity_value FROM entities WHERE entity_type = 'GPE';")
    return cursor.fetchall()

# Step 3: Geocode entity locations
def geocode_entity(entity_value):
    geolocator = Nominatim(user_agent="geo_coder")
    location = geolocator.geocode(entity_value)
    
    if location:
        return location.latitude, location.longitude, location.raw.get('display_name')
    else:
        return None, None, None

# Step 4: Store geocoded locations in database
def store_geocoded_location(cursor, entity_id, latitude, longitude, source):
    cursor.execute("""
        INSERT INTO geocoded_locations (entity_id, latitude, longitude, geocoding_source)
        VALUES (%s, %s, %s, %s);
    """, (entity_id, latitude, longitude, source))

# Step 5: Main function to run geocoding and store results
def run_geo_pipeline():
    print("[INFO] Starting geocoding process...")
    
    conn = connect_db()
    cursor = conn.cursor()

    entities = fetch_entities(cursor)

    for entity_id, entity_value in entities:
        latitude, longitude, source = geocode_entity(entity_value)
        
        if latitude and longitude:
            store_geocoded_location(cursor, entity_id, latitude, longitude, source)
            print(f"[INFO] Geocoded: {entity_value} -> {latitude}, {longitude}")
    
    conn.commit()
    cursor.close()
    conn.close()
    print("[INFO] Geocoding pipeline completed.")

if __name__ == "__main__":
    run_geo_pipeline()
