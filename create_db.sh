#!/bin/bash

DB_NAME="prediction_markets.db"
DDL_FILE="ddl.sql"

# Check if the DDL file exists
if [ ! -f "$DDL_FILE" ]; then
    echo "DDL file '$DDL_FILE' not found."
    exit 1
fi

# Remove the existing database file if it exists
if [ -f "$DB_NAME" ]; then
    rm "$DB_NAME"
    echo "Existing database file '$DB_NAME' removed."
fi

# Create a new SQLite3 database
sqlite3 "$DB_NAME" </dev/null
echo "New SQLite3 database '$DB_NAME' created."

# Read the DDL file and execute the SQL statements
sqlite3 "$DB_NAME" <"$DDL_FILE"
echo "DDL script executed successfully."
