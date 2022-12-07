#!/bin/bash

cd ~epower/epower

# Pull changes from Git, and check commit hashes
OLD_COMMIT=$(git log -n 1 --pretty=format:%H)
sudo -H -u epower bash -c "git pull -q"
NEW_COMMIT=$(git log -n 1 --pretty=format:%H)

# Run the upgrade script if new commits were got
if [ "$OLD_COMMIT" != "$NEW_COMMIT" ]; then
    bash ~epower/epower/upgrade_system.bash 2> ~epower/epower/logs/upgrade_errors.log
fi
