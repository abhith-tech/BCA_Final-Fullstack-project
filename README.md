# EmpowerAccess

EmpowerAccess is a voice-driven accessibility assistant and management platform that combines a Flask backend, a desktop Tkinter application, and web-based dashboards. It is designed for users who are specially disabled people for hands-free assistance, quick system control, and admin monitoring from one integrated experience.

## Overview

The project includes:

- A Flask backend for authentication, user management, weather/news/stock/system data, and admin APIs
- A desktop assistant application built with Tkinter for voice commands and system interactions
- Web pages for login, registration, user dashboard, and admin dashboard
- Optional packaging into a Windows executable with PyInstaller

## Key Features

- User registration, login, and profile management
- JWT-based authentication
- Voice assistant interactions with speech-to-text and text-to-speech
- Local system actions such as opening apps, managing files, clipboard actions, reminders, and basic OS controls
- Live information services for weather, news, stocks, and system info
- Emergency SOS flow with contact handling and SMS support
- Admin dashboard for user and activity monitoring
- Optional AI-powered request handling through Gemini-style integrations

## Project Structure

- app.py – Flask server and API routes
- gui_app.py – desktop application entry point
- config.py – shared app configuration
- core/ – command processing, routing, API client, voice handling, and tool execution
- ui/ – Tkinter UI windows, panels, toolbar, settings, and theming
- db/ – SQL schema files for users, logs, and admin data
- data/ – local JSON storage for reminders and memory
- *.html – web pages for login, registration, and dashboards
- PyInstaller build specification

## Requirements

### Software

- Python 3.10+
- MySQL server
- FFmpeg installed and available on your PATH
- Windows is the primary target for the desktop app

### Python packages

Install all dependencies with:

```bash
pip install -r requirements.txt
```

## Configuration

Before running the backend, set the following environment variables:

```bash
set JWT_SECRET=your-secret-key
set EMAIL_HOST=smtp.gmail.com
set EMAIL_PORT=587
set EMAIL_USER=your-email@gmail.com
set EMAIL_PASS=your-app-password
set EMAIL_FROM=your-email@gmail.com
set GEMINI_API_KEY=your-gemini-key
set TWILIO_ACCOUNT_SID=your-twilio-sid
set TWILIO_AUTH_TOKEN=your-twilio-token
set TWILIO_PHONE_FROM=your-twilio-number
```

You will also need to configure the MySQL connection inside app.py under DB_CONFIG.

## Database Setup

1. Create a MySQL database.
2. create the SQL files from the db/ folder.
3. Update the DB_CONFIG values in app.py to match your local database credentials.

## Running the Backend

Start the Flask server:

```bash
python app.py
```

The server will run at:

```text
http://localhost:5000
```

## Running the Desktop App

In a separate terminal, start the desktop assistant:

```bash
python gui_app.py
```

## Building the Windows Executable

To build a standalone Windows executable:

```bash
pyinstaller build.spec
```

The output will be generated in the build/ folder.

## Notes

- The desktop client expects the Flask backend to be running.
- Some features such as voice transcription and text-to-speech require the required audio and speech dependencies to be installed correctly.
- For production use, avoid running the Flask app in debug mode.

## License

This project is intended for local development and demonstration purposes unless a separate license is provided.
