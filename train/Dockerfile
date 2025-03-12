# Use the official Python image
FROM --platform=linux/amd64 python:3.13

# Set build arguments
ARG GOOGLE_CLOUD_PROJECT
ARG BASE_PATH

# Set them as environment variables
ENV GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT
ENV BASE_PATH=$BASE_PATH

# Set the working directory
WORKDIR /app

# Copy the script and dependencies
COPY . .

# Install dependencies
RUN pip install --no-cache-dir google-cloud-aiplatform kfp pandas prophet google-cloud-bigquery google-cloud-storage gcsfs db-dtypes

# Command to run the script
CMD ["python", "/app/train_pipeline.py"]
