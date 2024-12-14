# Tampa Development Coordination Locations - Datasette

This repository uses a Python script to import data from the GeoJSON endpoint into a SQLite database for use with [Datasette](https://datasette.io).

## Requirements

- Python 3.6+
- `requests` library
- `sqlite3` (included with Python)
- `geojson-to-sqlite` tool

## Installation

1. Install dependencies:

    ```bash
    pip install requests datasette geojson-to-sqlite
    ```

## Usage

1. Run the script:

    ```bash
    python script.py
    ```

   The script will:
   - Fetch GeoJSON from Tampa's ArcGIS endpoint
   - Create/update SQLite database (`data.db`)
   - Normalize timestamps (CREATEDDATE, LASTUPDATE)
   - Track new entries with `date_added`
   - Mark removed entries as `archived` with `date_archived`

2. Schedule daily updates (optional):

    ```bash
    crontab -e
    ```

    Add this line to run at midnight daily:
    ```cron
    0 0 * * * cd /path/to/project && /usr/bin/python script.py
    ```

## Deployment

Deploy with Datasette:

1. Start local server:

    ```bash
    datasette data.db
    ```

2. Deploy to cloud (optional):

    ```bash
    datasette publish cloudrun data.db
    ```

For more deployment options, see [Datasette documentation](https://docs.datasette.io/en/stable/publishing.html).

## Automated Deployment

This repository uses GitHub Actions to:
1. Run the script daily at midnight UTC
2. Deploy updated database to Vercel via datasette-publish-vercel

To set up automated deployment:

1. Create a Vercel account and get API token
2. Add token as GitHub repository secret named `VERCEL_TOKEN`
3. Enable GitHub Actions in repository settings
4. Push code to main branch to trigger initial deployment

The live deployment will be available at: `https://your-project-name.vercel.app`

## Data Structure

The database contains these fields:
- `RECORDID` (Primary Key)
- Location: `ADDRESS`, `UNIT`, `geometry` (GeoJSON Point)
- Status: `APPSTATUS`, `TENTATIVEHEARING`, `TENTATIVETIME`
- Metadata: `CREATEDDATE`, `LASTUPDATE` (ISO format)
- System: `date_added`, `date_archived`, `archived`

## Development

Temporary files:
- `temp.geojson` - Deleted after import
- [data.db](http://_vscodecontentref_/0) - SQLite database (add to .gitignore)

## License

Code is licensed under MIT. Data sourced from City of Tampa Open Data.