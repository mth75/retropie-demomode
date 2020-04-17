#!/usr/bin/env bash
# demo.sh
#############################################
# Lets the user enable the demo mode
#############################################

sudo pkill -f BGM.py
sudo pkill -f pngview
sudo -u pi python3 /usr/share/pyshared/rungames.py