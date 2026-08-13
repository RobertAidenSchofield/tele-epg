import os
import sys

def get_user_input():
    """
    Prompts the user for required environment variables and returns them as a dictionary.
    """
    print("--- Telegram EPG Docker Setup ---")
    print("Please provide the following configuration values. Press Enter to use defaults if available.")

    env_vars = {
        'API_ID': input("Enter your Telegram API_ID: "),
        'API_HASH': input("Enter your Telegram API_HASH: "),
        'PHONE_NUMBER': input("Enter your Telegram phone number (e.g., +1234567890): "),
        'TARGET_CHAT': input(
            "Enter the target Telegram chat ID (e.g., -1002001120719).\n"
            "Tip: After setup, run 'python scripts/get_chat_id.py' to find the correct ID.\n> "),
        'UPDATE_INTERVAL_HOURS': input("Enter the update interval in hours [default: 3]: ") or '3',
        'GITHUB_TOKEN': input("Enter your GitHub Personal Access Token for Gist updates: "),
        'GIST_ID': input("Enter the ID of the Gist to update: "),
    }

    # Basic validation
    for key, value in env_vars.items():
        if not value:
            print(f"\n[ERROR] {key} cannot be empty. Aborting setup.")
            sys.exit(1)

    print("\nConfiguration received. Proceeding with file generation...")
    return env_vars

def create_env_file(env_vars):
    """
    Creates a .env file from the user-provided variables.
    """
    print("-> Creating .env file...")
    try:
        with open('.env', 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
            # Add standard Python environment variable
            f.write("PYTHONUNBUFFERED=1\n")
        print("   .env file created successfully.")
    except IOError as e:
        print(f"[ERROR] Failed to write .env file: {e}")
        sys.exit(1)

def create_docker_compose():
    """
    Creates a docker-compose.yml file that uses the .env file.
    """
    print("-> Creating docker-compose.yml file...")
    docker_compose_content = """version: '3.8'

services:
  telegram-epg:
    build: .
    container_name: telegram_epg
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./data:/app/data
"""
    try:
        with open('docker-compose.yml', 'w') as f:
            f.write(docker_compose_content)
        print("   docker-compose.yml file created successfully.")
    except IOError as e:
        print(f"[ERROR] Failed to write docker-compose.yml file: {e}")
        sys.exit(1)

def create_data_directory():
    """
    Creates the data directory on the host to prepare for volume mounting.
    """
    print("-> Creating data directory...")
    try:
        os.makedirs('data', exist_ok=True)
        print("   'data' directory is ready.")
    except OSError as e:
        print(f"[ERROR] Failed to create data directory: {e}")
        sys.exit(1)


def create_dockerfile():
    """
    Creates the Dockerfile for the application.
    """
    print("-> Creating Dockerfile...")
    dockerfile_content = """# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for telethon with fast crypto
RUN apt-get update && apt-get install -y gcc libssl-dev && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Create a directory for the session data and EPG file
RUN mkdir -p /app/data

# Command to run the application
CMD ["python", "main.py"]
"""
    try:
        with open('Dockerfile', 'w') as f:
            f.write(dockerfile_content)
        print("   Dockerfile created successfully.")
    except IOError as e:
        print(f"[ERROR] Failed to write Dockerfile: {e}")
        sys.exit(1)

if __name__ == '__main__':
    config_vars = get_user_input()
    create_env_file(config_vars)
    create_docker_compose()
    create_dockerfile()
    create_data_directory()
    print("\n--- Setup Complete! ---")
    print("\nNext Steps:")
    print("1. If you don't know your Target Chat ID, run the following command:")
    print("   python scripts/get_chat_id.py")
    print("   (You may need to enter your credentials again and a 2FA code if enabled.)")
    print("2. Once you have the correct Chat ID, ensure it's updated in the '.env' file.")
    print("3. Start the service with:")
    print("   docker-compose up --build")