#!/usr/bin/env bash

# Start the Flask web app with Gunicorn
gunicorn --bind 0.0.0.0:$PORT admin_panel.app:app
