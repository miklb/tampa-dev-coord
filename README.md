# Tampa Development Coordination Locations - Datasette

This repository uses a Python script to import data from the City of Tampa's ArcGIS GeoJSON endpoint into a SQLite database for viewing with [Datasette](https://datasette.io).

## Requirements

- Python 3.11+
- `requests` library
- `datasette` (version 0.65.2 — latest stable; a 1.0 upgrade needs the template fork and metadata config redone, see Theming)
- `sqlite3` (included with Python)
- `geojson-to-sqlite` tool
- `datasette-geojson` plugin

## Installation

1. Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

2. Set up Python version:

    ```bash
    echo "3.11" > .python-version
    ```

## Usage

1. Run the script:

    ```bash
    python script.py
    ```

   The script will:
   - Fetch GeoJSON from Tampa's ArcGIS endpoint
   - Update SQLite database in `dev-locations/locations.db`
   - Archive removed records with timestamp
   - Convert Unix timestamps to ISO format

2. Run Datasette locally:

    ```bash
    datasette dev-locations/locations.db -m dev-locations/metadata.json \
      --template-dir dev-locations/templates \
      --setting suggest_facets off --setting default_page_size 50 \
      --static static:dev-locations/static
    ```

## Deployment

Deploy to Heroku:

```bash
datasette publish heroku dev-locations/locations.db \
  --metadata dev-locations/metadata.json \
  --template-dir dev-locations/templates \
  --static static:dev-locations/static \
  -n tampa-dev-coord-db
```

## Automated Deployment

This repository uses GitHub Actions to:
1. Run the script daily at midnight UTC
2. Commit database changes to the repository
3. Deploy the updated database to Heroku

The workflow file `.github/workflows/update-data.yml` handles:
- Scheduled runs
- Manual triggers
- Updates when code is pushed to main
- Deployment to Heroku with proper configuration

## Data Structure

The database contains these components:
- `current_full` - Complete table with all fields (hidden from public view)
- `archived_full` - Archive of removed records (hidden from public view)
- `current` - Public view with renamed columns and sensitive data removed
- `archived` - Public view of archived records

Key fields include:
- `RECORDID` (Primary Key)
- Location data: `ADDRESS`, `UNIT`, `geometry` (GeoJSON Point)
- Status data: `APPSTATUS`, `TENTATIVEHEARING`, `TENTATIVETIME`
- Type information: `RECORDALIAS` (displayed as "Type")
- Metadata: `CREATEDDATE`, `LASTUPDATE` (ISO format)
- For archived records: `archived_date`

## Configuration

### Metadata

The `dev-locations/metadata.json` file configures:
- Database title and description
- Table display options
- Custom facets
- CSS styling
- Table permissions

### Settings

Configure Datasette with environment variables or the `--setting` flag:

```bash
datasette dev-locations/locations.db --setting suggest_facets off --setting default_page_size 50
```

## Theming

The site is themed to match [The Tampa Monitor](https://tampamonitor.com/)'s design
system. `~/Sites/tm-static` is the source of truth; shared CSS and fonts are copied
in verbatim (never hand-edited here) by a sync script:

```bash
node scripts/sync-design.js           # copy anything that drifted from tm-static
node scripts/sync-design.js --check   # report drift without writing (exit 1 if any)
```

How it fits together:
- `dev-locations/templates/` - forked `base.html` wraps every Datasette page in the
  Monitor chrome (`_monitor_header.html`, `_monitor_footer.html`); `index.html` is a
  custom homepage. Activated by the `--template-dir` flag (Procfile + commands above).
- `dev-locations/static/css/site.css` - the stylesheet entry point. It imports
  Datasette's own `app.css` into the **lowest cascade layer** so the synced
  design-system layers (and `theme.css`) can override it; the stock unlayered
  `app.css` link is removed in the forked `base.html`. Don't re-add it.
- `dev-locations/static/css/theme.css` - the only hand-edited CSS file: all
  dev-coord-specific styling (Datasette UI retheme, homepage). It must stay the
  last import in `site.css`.
- Everything else under `static/css/` and `static/fonts/` is a pristine synced copy.

## Development

Project structure:
- `dev-locations/` - Main directory containing database and config
- `dev-locations/templates/` - Custom Datasette templates (Monitor chrome + homepage)
- `dev-locations/static/css/`, `dev-locations/static/fonts/` - Design system (synced from tm-static, see Theming)
- `scripts/sync-design.js` - One-way design-system sync from tm-static
- `script.py` - Main data processing script
- `Procfile` - Defines Heroku web process

Temporary files:
- `temp.geojson` - Deleted after import

## License

Code is licensed under MIT. Data sourced from City of Tampa Open Data.