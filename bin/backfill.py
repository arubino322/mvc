import argparse
import json
import os
from datetime import datetime, timedelta

import requests
from google.cloud import bigquery

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f"Not a valid date: '{date_str}'.")

def delete_existing_data(client, project_id, dataset_id, table_id, dt):
    delete_query = f"""
        DELETE FROM `{project_id}.{dataset_id}.{table_id}`
        WHERE crash_date = '{dt}'
    """
    query_job = client.query(delete_query)
    query_job.result()
    print('Existing data deleted')

def insert_data(client, dt, table, api_key, secret_key, schema):
    endpoint_mapping = {
        "crashes": "h9gi-nx95",
        "person": "f55k-p6yu"
    }
    endpoint = endpoint_mapping[table]

    url = f"https://data.cityofnewyork.us/resource/{endpoint}.json?$where=crash_date = '{dt}T00:00:00' limit 50000"
    response = requests.get(url, auth=(api_key, secret_key))
    if response.status_code != 200:
        return f"Error fetching data: {response.status_code}, {response.text}"
    collisions = response.json()

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
    errors = client.insert_rows_json(f'nyc-transit-426211.motor_vehicle_crashes.{table}', rows_to_insert)
    if errors:
        return f"Encountered errors while inserting rows: {errors}"
    print(f"Inserted {str(len(collisions))} rows for {dt}")


def main(start_date, end_date, table):

    api_key, secret_key = os.environ['NYCT_API_KEY'], os.environ['NYCT_SECRET_KEY']
    project_id = 'nyc-transit-426211'
    dataset_id = 'motor_vehicle_crashes'

    # Connect to BQ
    client = bigquery.Client(project='nyc-transit-426211')
    table_ref = client.dataset('motor_vehicle_crashes').table(table)
    table_object = client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
    )

    # Get the table schema
    schema = {field.name: field.field_type for field in table_object.schema}

    print(f"Running backfill for dates from {start_date.date()} to {end_date.date()}")
    
    # Define API endpoint and params
    while start_date <= end_date:
        dt = start_date.strftime('%Y-%m-%d')
        print(f"Date: {dt}")
        # delete if exists
        # delete_existing_data(client, project_id, dataset_id, table_id, dt)

        # insert data
        insert_data(client, dt, table, api_key, secret_key, schema)

        # iterate by 1 day
        start_date = start_date + timedelta(days=1)

    return "Data successfully written to BQ"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill collisions data based on date range")
    parser.add_argument("--start_date", type=validate_date, required=True, help="Start date in YYYY-MM-DD format")
    parser.add_argument("--end_date", type=validate_date, required=True, help="End date in YYYY-MM-DD format")
    parser.add_argument("--table", required=True, choices = ['crashes', 'person'], help="crashes or person")
    parser.add_argument("--dryrun", action="store_true", help="If specified, only print the dates without executing the main logic.")

    args = parser.parse_args()

    if args.dryrun:
        print(f"DRY RUN: Dates to be backfilled for {args.table} - Start Date: {args.start_date.date()}, End Date: {args.end_date.date()}")
    else:
        main(args.start_date, args.end_date, args.table)
