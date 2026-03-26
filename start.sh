#!/usr/bin/env bash

# Run the Telegram bot in the background
python -m bot.main &

# Start the Flask web app with Gunicorn
gunicorn --bind 0.0.0.0:$PORT admin_panel.app:app
