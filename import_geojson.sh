#!/bin/bash

# URL to fetch GeoJSON data
URL="https://arcgis.tampagov.net/arcgis/rest/services/OpenData/Planning/MapServer/31/query?outFields=*&where=1%3D1&f=geojson"

# Temporary file to store GeoJSON data
TEMP_FILE=$(mktemp)

# Fetch GeoJSON data and save to temporary file
curl -s "$URL" -o "$TEMP_FILE"

# Import GeoJSON data to SQLite
geojson-to-sqlite data.db data "$TEMP_FILE" --pk=RECORDID

# Remove temporary file
rm "$TEMP_FILE"