#!/bin/bash

# Upgrade Python packages
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && pip install -q -U pip"
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && pip install -q -U -r requirements"

# Do basic Django updates
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && ./manage.py migrate -v 0"
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && ./manage.py collectstatic --noinput -v 0"
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && ./manage.py compilemessages -v 0"

# Restart uWSGI
service uwsgi restart
