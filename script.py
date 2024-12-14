import sqlite3
import requests
import subprocess
import json
from datetime import datetime
from pathlib import Path

URL = "https://arcgis.tampagov.net/arcgis/rest/services/OpenData/Planning/MapServer/31/query?outFields=*&where=1%3D1&f=geojson"

def fetch_geojson():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        # Save GeoJSON to temp file
        with open('temp.geojson', 'w') as f:
            f.write(response.text)
        return True
    except (requests.RequestException, ValueError) as e:
        print(f"Error fetching data: {e}")
        return False

def convert_timestamp(ts):
    """Convert Unix timestamp in milliseconds to ISO format"""
    if ts:
        return datetime.fromtimestamp(ts/1000.0).isoformat()
    return None

def main():
    conn = sqlite3.connect("data.db")
    cursor = conn.cursor()

    # Add date_archived column
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data (
        id INTEGER,
        OBJECTID INTEGER,
        RECORDID TEXT PRIMARY KEY,
        ADDRESS TEXT,
        UNIT TEXT,
        APPSTATUS TEXT,
        TENTATIVEHEARING TEXT,
        TENTATIVETIME TEXT,
        RECORDALIAS TEXT,
        MAPDOT TEXT,
        CRA TEXT,
        NEIGHBORHOOD TEXT,
        COUNCILDISTRICT TEXT,
        CREATED TEXT,
        CREATEDDATE INTEGER,
        LASTUPDATE INTEGER,
        LASTEDITOR TEXT,
        GlobalID TEXT,
        URL TEXT,
        geometry TEXT,
        date_added TEXT,
        date_archived TEXT,
        archived INTEGER DEFAULT 0
    )
    """)

    if fetch_geojson():
        # Import new data
        subprocess.run([
            'geojson-to-sqlite',
            'data.db',
            'data',
            'temp.geojson',
            '--pk=RECORDID'
        ])

        cursor.execute("""
        UPDATE data 
        SET 
            CREATEDDATE = strftime('%Y-%m-%dT%H:%M:%SZ', datetime(CREATEDDATE/1000, 'unixepoch')),
            LASTUPDATE = strftime('%Y-%m-%dT%H:%M:%SZ', datetime(LASTUPDATE/1000, 'unixepoch'))
        WHERE CREATEDDATE IS NOT NULL 
          AND LASTUPDATE IS NOT NULL
          AND CREATEDDATE > 0
          AND LASTUPDATE > 0
        """)

        # Get current RECORDIDs from feed
        with open('temp.geojson') as f:
            geojson = json.loads(f.read())
            current_ids = {feature["properties"]["RECORDID"] 
                         for feature in geojson["features"]}

        # Archive records not in current feed
        cursor.execute("""
        UPDATE data 
        SET 
            archived = 1,
            date_archived = ?
        WHERE RECORDID NOT IN ({})
        AND archived = 0
        """.format(','.join('?' * len(current_ids))), 
        (datetime.now().isoformat(), *current_ids))

        # Update date_added for new records
        cursor.execute("""
        UPDATE data 
        SET date_added = ?
        WHERE date_added IS NULL
        """, (datetime.now().isoformat(),))

        Path('temp.geojson').unlink(missing_ok=True)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()