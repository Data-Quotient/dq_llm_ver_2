# Use the official Python 3.11 image as a base
FROM python:3.11-slim

# Set environment variables to reduce Python package issues and turn off buffering
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set the working directory in the container
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files to the container
COPY pyproject.toml poetry.lock /app/

# Install Python dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Copy the Django project to the container
COPY . /app/

# Install the TaskWeaver package as an editable package
RUN pip install -e ./pkgs/TaskWeaver


# Expose the port the app runs on
EXPOSE 8080

# Command to run the application using Daphne
CMD ["poetry", "run", "daphne", "-b", "0.0.0.0", "-p", "8080", "dq_llm.asgi:application"]
