#!/bin/sh
python genblog.py
python gen-kb-html.py ../www/kb ../srcblog/knowledge-base.txt
