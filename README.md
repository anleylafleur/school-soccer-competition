# Single Flask Application

This package combines the FIFA Registry hierarchy and the School Soccer Competition modules into one Flask application.

## Main routes

- `/admin` dashboard
- `/worlds`, `/confederations`, `/countries`, `/states`, `/regions`, `/associations`, `/clubs`, `/teams`, `/players`
- `/hierarchy`
- `/schools`, `/competitions`, `/fixtures`, `/results`
- `/upload-schools`
- `/db-test`

## Render environment variables

Set these in Render:

- `DB_SERVER`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `SECRET_KEY`

Use Docker runtime so SQL Server ODBC Driver 18 is installed.
