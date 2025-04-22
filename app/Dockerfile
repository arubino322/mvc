FROM python:3.12-slim

# Set build arguments
ARG GOOGLE_CLOUD_PROJECT
ARG BASE_PATH
ARG CREDENTIAL_PATH

# Set them as environment variables
ENV GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT}
ENV BASE_PATH=${BASE_PATH}
ENV CREDENTIAL_PATH=${CREDENTIAL_PATH}

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip3 install -r requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]