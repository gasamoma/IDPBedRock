#!/bin/sh
rm -rf lib
pip3 install -r requirements-dev.txt --target=./lib/python -U
