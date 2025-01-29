import json
import os
from datetime import datetime, timedelta

import requests
from flask import Request
from google.cloud import bigquery


def fetch_and_store(request: Request):
    if request.method == 'POST':
        request_json = request.get_json(silent=True)
    else:
        return 'Invalid request method', 405
    
    project_id = 'nyc-transit-426211'
    dataset_id = 'motor_vehicle_crashes'
    table_id = 'collisions'
    api_key, secret_key = os.environ['NYCT_API_KEY'], os.environ['NYCT_SECRET_KEY']

    # Define API endpoint and params
    collision_dt = (datetime.today() - timedelta(days=6)).strftime('%Y-%m-%d')
    url = f"https://data.cityofnewyork.us/resource/f55k-p6yu.json?$where=crash_date = '{collision_dt}'"
    response = requests.get(url, auth=(api_key, secret_key))
    if response.status_code != 200:
        return f"Error fetching data: {response.status_code}, {response.text}"
    collisions = response.json()

    # Connect to BQ
    client = bigquery.Client(project=project_id)
    table_ref = client.dataset(dataset_id).table(table_id)
    table = client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    )

    # Get the table schema
    schema = {field.name: field.field_type for field in table.schema}

    # Insert rows
    rows_to_insert = []
    for record in collisions:
        formatted_record = {}
        for key, field_type in schema.items():
            value = record.get(key)
            if field_type == 'DATE' and value:
                value = datetime.strftime(datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f'), '%Y-%m-%d')
            formatted_record[key] = value
        rows_to_insert.append(formatted_record)

    errors = client.insert_rows_json('nyc-transit-426211.motor_vehicle_crashes.collisions', rows_to_insert)
    if errors:
        return f"Encountered errors while inserting rows: {errors}"
    return "Data successfully written to BQ"
