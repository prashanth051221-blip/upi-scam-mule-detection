#!/usr/bin/env python
"""Django entry point.  Run from the project folder:  python web/manage.py runserver"""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upi_site.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
