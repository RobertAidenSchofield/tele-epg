# Telegram to EPG Generator

This project is a Python-based application designed to automatically fetch Electronic Program Guide (EPG) event listings from a Telegram chat, parse them, and generate a standard XMLTV file (`epg.xml`). It can also upload the generated file to a GitHub Gist, making it accessible for use in IPTV players and other EPG clients. The entire application is containerized with Docker for easy setup and deployment.

## Features

- **Automated EPG Generation**: Runs on a schedule to fetch the latest data from Telegram.
- **Flexible Parsing**: Supports multiple message formats for EPG events using a pattern-based system.
- **XMLTV Compliant**: Generates a standard `epg.xml` file compatible with most IPTV clients.
- **Data Persistence**: Updates and merges new events with existing program data from previous runs.
- **GitHub Gist Integration**: Automatically uploads the generated EPG to a specified GitHub Gist.
- **Dockerized**: Easy to set up and run in a containerized environment.
- **Interactive Setup**: Includes helper scripts for a smooth configuration process.

## Prerequisites

Before you begin, ensure you have the following installed:

- Docker
- Docker Compose
- Python 3.8+ (for running the setup scripts)

You will also need:

- A Telegram account.
- Telegram API credentials (`API_ID` and `API_HASH`). You can get these from my.telegram.org.
- A GitHub Personal Access Token with the `gist` scope enabled. You can create one here.

## Setup and Installation

Follow these steps to get the application up and running.

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/tele-epg.git
cd tele-epg
```

### 2. Run the Interactive Setup Script

The setup script will prompt you for your credentials and generate the necessary Docker configuration files (`.env`, `docker-compose.yml`, and `Dockerfile`).

```bash
python scripts/setup.py
```

You will be asked to enter the following information:

- `API_ID` & `API_HASH`
- `PHONE_NUMBER`
- `TARGET_CHAT` (you can enter a temporary value and find the correct one in the next step)
- `GITHUB_TOKEN`
- `GIST_ID`

### 3. Find Your Target Chat ID

To get EPG data, the application needs to know which Telegram chat to monitor. A helper script is included to find the correct ID.

Run the script:

```bash
python scripts/get_chat_id.py
```

The script will connect to your Telegram account (you may be prompted for a login code) and list your recent chats with their corresponding IDs.

```
--- Telegram Chat ID Finder ---
Listing your recent chats and their IDs...

Chat Name                                          | Chat ID
--------------------------------------------------------------------------------
My EPG Channel                                     | -1002002220719
John Doe                                           | 123456789
Some Group                                         | -987654321
```

Copy the correct ID and update the `TARGET_CHAT` variable in the `.env` file that was created in the previous step.

### 4. Build and Run the Docker Container

Once your `.env` file is correctly configured, you can build and start the Docker container in detached mode:

```bash
docker-compose up --build -d
```

The application will now start, fetch the initial data, and then run on the schedule you defined (`UPDATE_INTERVAL_HOURS`).

## Configuration

All configuration is managed through the `.env` file. Here are the available variables:

| Variable                | Description                                                                 |
| ----------------------- | --------------------------------------------------------------------------- |
| `API_ID`                | Your Telegram application API ID.                                           |
| `API_HASH`              | Your Telegram application API hash.                                         |
| `PHONE_NUMBER`          | The phone number associated with your Telegram account.                     |
| `TARGET_CHAT`           | The ID of the Telegram chat/channel to fetch messages from.                 |
| `UPDATE_INTERVAL_HOURS` | The interval in hours at which the script will run to refresh the EPG data. |
| `GITHUB_TOKEN`          | Your GitHub Personal Access Token for updating the Gist.                    |
| `GIST_ID`               | The ID of the GitHub Gist where the `epg.xml` file will be uploaded.        |

## Project Structure

The project is organized into the following directories:

- `app/`: Contains the core application logic, including the Telegram client, parser, and EPG generator.
- `data/`: A volume-mounted directory to store the Telegram session file and the generated `epg.xml`.
- `scripts/`: Holds helper scripts for setup and configuration.
- `main.py`: The main entry point for the application.
- `Dockerfile` & `docker-compose.yml`: Docker configuration files.

### A Note on Generated Files

The setup script creates several files for you (`.env`, `docker-compose.yml`, `Dockerfile`) and a `data` directory. A `.gitignore` file is included to ensure that sensitive information (in `.env`) and generated data (in `data/` and `*.session`) are not committed to source control.

The `data` directory is used by the Docker container as a persistent volume to store:

- `telegram_session.session`: Your authenticated Telegram session.
- `epg.xml`: The generated XMLTV file.

