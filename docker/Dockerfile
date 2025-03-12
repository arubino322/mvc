# Python base image
FROM python:3.13

# Install Poetry
RUN pip install poetry

# Copy project files
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-dev

# Runtime stage
FROM python:3.13
WORKDIR /app

# Copy installed dependencies from the builder stage
COPY --from=builder /root/.cache/pypoetry/virtualenvs /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project viles
COPY . /app

# Command to run the training script
CMD ["python", "train_pipeline.py"]
