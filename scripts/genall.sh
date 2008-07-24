#!/bin/sh
# remove previously generated *html files
rm -rf ../www/200*
python genblog.py
python gen-kb-html.py ../www/kb ../srcblog/knowledge-base.txt
