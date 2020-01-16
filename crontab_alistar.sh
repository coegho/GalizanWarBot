#!/bin/bash
cd /home/<your_user>/galizawarbot
source env/bin/activate
PYTHONIOENCODING=UTF-8 python alistarse.py >> output.txt 2>> errors.txt
