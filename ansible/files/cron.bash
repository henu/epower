#!/bin/bash
set -e
cd ~/epower
source venv/bin/activate
./manage.py run_periodic_tasks >/dev/null 2> ~/epower/logs/errors.log
