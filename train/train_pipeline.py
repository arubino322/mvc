import os
from datetime import datetime, timedelta
from kfp import dsl, compiler
from kfp.dsl import component
import google.cloud.aiplatform as aip

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
BASE_PATH = os.getenv("BASE_PATH")

@component(
    base_image='python:3.13',
    packages_to_install=['db-dtypes', 'pandas', 'prophet', 'google-cloud-bigquery', 'google-cloud-storage', 'gcsfs']
)
def preprocess_and_train(base_path: str, dt: str) -> str:
    import gcsfs
    import pandas as pd
    import pickle
    from google.cloud import bigquery
    from prophet import Prophet

    project_name = "nyc-transit-426211"
    dataset = "motor_vehicle_crashes"
    table = "crashes"
    model_path = f"{base_path}/trained_models/model_{dt}.pickle"

    client = bigquery.Client(project=project_name)
    query = f"""
        select
            crash_date as ds,
            count(*) as y
        from `{project_name}.{dataset}.{table}`
        where crash_date <= '{dt}'
        group by 1
        order by 1 asc
    """
    df = client.query(query).to_dataframe()

    # Train model
    model = Prophet()
    model.fit(df)
    print("Training complete!")

    # Save the model to GCS
    fs = gcsfs.GCSFileSystem()
    with fs.open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    return base_path

@component(
    base_image='python:3.13',
    packages_to_install=['pandas', 'google-cloud-storage', 'gcsfs', 'prophet']
)
def write_predictions(base_path: str, dt: str) -> None:
    import pandas as pd
    import gcsfs
    import pickle
    from prophet import Prophet

    model_path = f"{base_path}/trained_models/model_{dt}.pickle"
    predictions_path = f"{base_path}/predictions/{dt}/predictions.csv"

    fs = gcsfs.GCSFileSystem()
    
    # Load trained model
    with fs.open(model_path, 'rb') as model_file:
        model = pickle.load(model_file)
    
    # Generate predictions
    predictions = model.make_future_dataframe(periods=1)
    forecast = model.predict(predictions)

    # Save predictions to GCS
    with fs.open(predictions_path, 'w') as f:
        forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(1).to_csv(f, index=False)

@dsl.pipeline(
    name='motor-vehicle-crashes-pipeline',
    description='An pipeline that trains and evaluates NYC motor vehicle crashes.'
)
def mvc_pipeline():
    dt = (datetime.today() - timedelta(days=61)).strftime('%Y-%m-%d')
    preprocess_and_train_task = preprocess_and_train(base_path=BASE_PATH, dt=dt)
    write_predictions(base_path=preprocess_and_train_task.output, dt=dt)

def compile_and_run_pipeline():
    pipeline_filename = "preprocess_train_evaluate.json"
    compiler.Compiler().compile(pipeline_func=mvc_pipeline,
                                package_path=pipeline_filename
    )

    job = aip.PipelineJob(
        display_name="mvc_pipeline",
        template_path=pipeline_filename,
        project=GOOGLE_CLOUD_PROJECT,
    )
    job.submit()

if __name__ == "__main__":
    compile_and_run_pipeline()
