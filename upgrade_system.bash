#!/bin/bash

# Upgrade Python packages
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && pip install -q -U pip"
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && pip install -q -U -r requirements"

# Do basic Django updates
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && ./manage.py migrate -v 0"
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && ./manage.py collectstatic --noinput -v 0"
sudo -H -u epower bash -c "cd ~epower/epower && source venv/bin/activate && ./manage.py compilemessages -v 0"

# Restart uWSGI
/usr/sbin/service uwsgi restart

# Upgrade the script that checks updates
cp ~epower/epower/ansible/files/check_updates.bash ~/check_updates.bash
chmod +x ~/check_updates.bash

# Upgrade the cron script
sudo -H -u epower bash -c "cp ~epower/epower/ansible/files/cron.bash ~epower/epower/cron.bash"
sudo -H -u epower bash -c "chmod +x ~epower/epower/cron.bash"
