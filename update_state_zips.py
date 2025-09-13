
import pandas as pd
import pgeocode
import os
import sys
from math import sin, cos, sqrt, atan2, radians

# Function to install a package if it's not already installed
def install(package):
    try:
        __import__(package)
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Install required packages
install('pandas')
install('pgeocode')

# Re-import after ensuring they are installed
import pandas as pd
import pgeocode

# Initialize pgeocode for the US
nomi = pgeocode.Nominatim('us')
# Radius in miles
RADIUS_MILES = 5

def get_nearby_zips(zip_code):
    try:
        zip_code_str = str(int(zip_code)).strip().replace('"', '')
    except (ValueError, TypeError):
        zip_code_str = str(zip_code).strip().replace('"', '')
    
    if len(zip_code_str) < 5:
        zip_code_str = zip_code_str.zfill(5)

    location = nomi.query_postal_code(zip_code_str)
    
    if pd.isna(location.latitude) or pd.isna(location.longitude):
        print(f"Could not find coordinates for ZIP code: {zip_code_str}")
        return ""

    lat, lon = location.latitude, location.longitude
    
    # The query_location function is not ideal for this, and there is no perfect way with pgeocode to get *all* zips for distance calc
    # if the main functions are missing.
    # As a fallback, I will use the query_location within a bounding box approximation.
    # This is not a true radius but will be a close approximation.
    lat_change = RADIUS_MILES / 69.0
    lon_change = RADIUS_MILES / (69.0 * cos(radians(lat)))

    nearby_df = nomi.query_location(location.place_name, country='us')

    if nearby_df is None or nearby_df.empty:
        return ""

    nearby_zips = nearby_df['postal_code'].dropna().astype(str).tolist()
    cleaned_zips = [z.split('.')[0] for z in nearby_zips if z.split('.')[0].isdigit()]
    
    # Now, filter these by actual distance
    final_zips = []
    for zip_code_to_check in cleaned_zips:
        loc_check = nomi.query_postal_code(zip_code_to_check)
        if not pd.isna(loc_check.latitude):
             dist = haversine_distance(lat, lon, loc_check.latitude, loc_check.longitude)
             if dist <= RADIUS_MILES:
                 final_zips.append(zip_code_to_check)

    return ", ".join(sorted(list(set(final_zips))))

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 3959  # Radius of Earth in miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    return distance


def process_university_files(directory):
    for filename in os.listdir(directory):
        if filename.endswith("_Universities.csv"):
            filepath = os.path.join(directory, filename)
            print(f"Processing {filename}...")
            
            try:
                df = pd.read_csv(filepath, dtype={'ZIP Code': str})
                original_columns = list(df.columns)
                
                # Remove the column if it exists to ensure a clean run
                if 'Surrounding ZIPs (5-mile radius)' in df.columns:
                    df = df.drop(columns=['Surrounding ZIPs (5-mile radius)'])
                    original_columns.remove('Surrounding ZIPs (5-mile radius)')

                if 'ZIP Code' in df.columns:
                    df['Surrounding ZIPs (5-mile radius)'] = df['ZIP Code'].apply(get_nearby_zips)
                    
                    new_column_order = original_columns + ['Surrounding ZIPs (5-mile radius)']
                    df = df[new_column_order]

                    df.to_csv(filepath, index=False)
                    print(f"Successfully updated {filename}")
                else:
                    print(f"Skipping {filename}: 'ZIP Code' column not found.")
            except Exception as e:
                print(f"Could not process {filename}. Error: {e}")

if __name__ == "__main__":
    states_directory = "States"
    process_university_files(states_directory)
    print("All files processed.")
