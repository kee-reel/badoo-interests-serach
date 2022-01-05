#!/bin/bash

python3 selenium_profiles.py &
cpulimit -l 80 -p $!
