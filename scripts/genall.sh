#!/bin/sh
# remove previously generated *html files
rm -rf ../www/200* ../www/blog
python genblog.py
python genkbhtml.py
