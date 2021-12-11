#!/usr/bin/env bash
# demo.sh
#############################################
# Lets the user enable the demo mode
#############################################

sudo pkill -f joy2key_sdl.py
sudo -u pi python3 /usr/share/pyshared/rungames.py
