import sqlite3
import requests
import subprocess
import json
from datetime import datetime
from pathlib import Path
import time

URL = "https://arcgis.tampagov.net/arcgis/rest/services/OpenData/Planning/MapServer/31/query?outFields=*&where=1%3D1&f=geojson"
DB_PATH = "dev-locations/locations.db"
TIMEOUT = 20

def convert_timestamp(ts):
    """Convert Unix timestamp in milliseconds to ISO format"""
    if ts:
        return datetime.fromtimestamp(ts/1000.0).isoformat()
    return None

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=TIMEOUT)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA journal_mode=DELETE")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS current_full (
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
        geometry TEXT
    )""")
    
    cursor.execute("""CREATE VIEW IF NOT EXISTS current AS 
        SELECT 
            RECORDID,
            ADDRESS,
            UNIT,
            RECORDALIAS as Type,
            CRA,
            NEIGHBORHOOD,
            COUNCILDISTRICT,
            CREATEDDATE,
            LASTUPDATE,
            URL,
            geometry
        FROM current_full
    """)
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS archived (
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
        archived_date TEXT
    )""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS archived_full (
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
        archived_date TEXT
    )""")
    
    cursor.execute("""CREATE VIEW IF NOT EXISTS archived AS 
        SELECT 
            RECORDID,
            ADDRESS,
            UNIT,
            RECORDALIAS as Type,
            MAPDOT,
            CRA,
            NEIGHBORHOOD,
            COUNCILDISTRICT,
            CREATEDDATE,
            LASTUPDATE,
            URL,
            geometry,
            archived_date
        FROM archived_full
    """)
    
    return conn, cursor

def fetch_geojson():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        with open('temp.geojson', 'w') as f:
            f.write(response.text)
        return True
    except (requests.RequestException, ValueError) as e:
        print(f"Error fetching data: {e}")
        return False

def archive_missing_records(cursor, conn, current_ids):
    cursor.execute("""
    INSERT INTO archived_full
    SELECT *, datetime('now')
    FROM current_full 
    WHERE RECORDID NOT IN ({})
    """.format(','.join('?' * len(current_ids))), current_ids)
    
    cursor.execute("""
    DELETE FROM current_full 
    WHERE RECORDID NOT IN ({})
    """.format(','.join('?' * len(current_ids))), current_ids)
    conn.commit()

def import_geojson():
    subprocess.run([
        'geojson-to-sqlite',
        DB_PATH,
        'current_full',  # Change target to table instead of view
        'temp.geojson',
        '--pk=RECORDID'
    ], check=True)

def convert_dates(cursor, conn):
    cursor.execute("""
    UPDATE current_full SET
        CREATEDDATE = strftime('%Y-%m-%dT%H:%M:%SZ', datetime(CREATEDDATE/1000, 'unixepoch')),
        LASTUPDATE = strftime('%Y-%m-%dT%H:%M:%SZ', datetime(LASTUPDATE/1000, 'unixepoch'))
    WHERE CREATEDDATE IS NOT NULL 
        AND LASTUPDATE IS NOT NULL
        AND CREATEDDATE > 0
        AND LASTUPDATE > 0
    """)
    conn.commit()

def cleanup_db_files():
    """Remove SQLite journal files before serving with datasette"""
    for ext in ['-wal', '-shm', '-journal']:
        Path(f"{DB_PATH}{ext}").unlink(missing_ok=True)

def main():
    try:
        # Clean up any stale WAL files
        cleanup_db_files()
        
        conn, cursor = init_db()
        
        if fetch_geojson():
            response = requests.get(URL)
            data = response.json()
            if 'features' not in data:
                print("Error: Missing 'features' in response")
                return
                
            current_records = data['features']
            current_ids = [r['properties']['RECORDID'] for r in current_records]
            
            archive_missing_records(cursor, conn, current_ids)
            conn.close()
            
            import_geojson()
            
            # Reopen connection and convert dates
            conn = sqlite3.connect(DB_PATH, timeout=TIMEOUT)
            cursor = conn.cursor()
            convert_dates(cursor, conn)
            conn.close()
            
        Path('temp.geojson').unlink(missing_ok=True)
        
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
        cleanup_db_files()

if __name__ == "__main__":
    main()