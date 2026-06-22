# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies (ffmpeg for voice recognition)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Environment variables will be passed via docker-compose or -e flag
# We don't expose ports because the bot uses polling

# Run the bot
CMD ["python", "main.py"]
