#!/bin/bash
gunicorn asgi:app -c gunicorn_config.py
