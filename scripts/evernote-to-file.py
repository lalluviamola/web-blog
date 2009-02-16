#!/usr/bin/env python
import sys, os.path, datetime, codecs
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# All text is saved to OUT_FILE
OUT_FILE = os.path.join(SCRIPT_DIR, "..", "srcblog", "evernote-utf8.txt")

EVERNOTE_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Evernote", "data")
# this might be different, depending on the Evernote version
EVERNOTE_DIR = os.path.join(EVERNOTE_DIR, "40145")
EVERNOTE_DB_PATH = os.path.join(EVERNOTE_DIR, "Evernote.sql")
EVERNOTE_CONTENT_DIR = os.path.join(EVERNOTE_DIR, "content")

g_conn = None
def get_conn():
    global g_conn
    if not g_conn:
        g_conn = sqlite3.connect(EVERNOTE_DB_PATH)
    return g_conn

def close_conn():
    global g_conn
    if g_conn:
        g_conn.close()
        g_conn = None

g_article_to_tags_map = None
def get_article_to_tags_map():
    global g_article_to_tags_map
    if g_article_to_tags_map:
        return g_article_to_tags_map
    conn = get_conn()
    c = conn.cursor()
    c.execute("select Z_3NOTES, Z_7TAGS from Z_3TAGS")
    d = {}
    for row in c:
        article_id = row[0]
        tag_id = row[1]
        if article_id in d:
            d[article_id].append(tag_id)
        else:
            d[article_id] = [tag_id]
    c.close()
    g_article_to_tags_map = d
    return g_article_to_tags_map

g_tag_to_name_map = None
def get_tag_to_name_map():
    global g_tag_to_name_map
    if g_tag_to_name_map:
        return g_tag_to_name_map
    conn = get_conn()
    c = conn.cursor()
    c.execute("select Z_PK, ZNAME2 from ZENSERVICEENTITY where Z_ENT = 7")
    d = {}
    for row in c:
        tag_id = row[0]
        tag_name = row[1]
        d[tag_id] = tag_name
    c.close()
    g_tag_to_name_map = d
    return g_tag_to_name_map

def tags_for_article(article_id):
    article_to_tags_map = get_article_to_tags_map()
    if article_id not in article_to_tags_map:
        return None
    tag_ids = article_to_tags_map[article_id]
    tag_to_name_map = get_tag_to_name_map()
    tags = [tag_to_name_map[tag_id] for tag_id in tag_ids]
    return tags

def datetime_to_str(dt): return dt.strftime('%Y-%m-%d %H:%M:%S')

def get_content(content_enml_path):
    fo = codecs.open(content_enml_path, "r", "utf-8")
    txt = fo.read()
    fo.close()
    en_note_tag_start = txt.find("<en-note")
    assert -1 != en_note_tag_start
    en_note_tag_end = txt.find(">", en_note_tag_start)
    assert -1 != en_note_tag_end
    en_note_end = txt.find("</en-note", en_note_tag_end)
    assert -1 != en_note_end
    txt = txt[en_note_tag_end+1:en_note_end]
    return txt.encode("utf-8")

def extract_articles():
    txt_lines = []
    conn = get_conn()
    c = conn.cursor()
    c.execute("select Z_PK, ZTITLE, ZCREATED from ZENSERVICEENTITY where Z_ENT = 3")
    # ZCREATED timestamp is in weird format that looks like 31 years after
    # unix timestamp. so this is a crude way to approximate this. Might be off
    # by a day or so
    td = datetime.timedelta(days=31*365+9)
    for row in c:
        article_id = row[0]
        title = row[1]
        #created_on = datetime.datetime.fromtimestamp(row[2])
        created_on = datetime.datetime.fromtimestamp(row[2])
        created_on = created_on + td
        title_line = u"@Title: %s" % title
        print(title_line)
        date_line = "@Date: %s" % datetime_to_str(created_on)
        print(date_line)
        tags = tags_for_article(article_id)
        tags_line_utf8 = None
        if tags:
            tags_line = "@Tags: %s" % u", ".join(tags)
            tags_line_utf8 = tags_line.encode("utf-8")
            print(tags_line)
        content_enml_path = os.path.join(EVERNOTE_CONTENT_DIR, "p%s" % article_id, "content.enml")
        content_utf8 = get_content(content_enml_path)
        #print(content_utf8)
        #print("")

        txt_lines.append(title_line.encode("utf-8"))
        txt_lines.append(date_line.encode("utf-8"))
        if tags_line_utf8:
            txt_lines.append(tags_line_utf8)
        txt_lines.append(content_utf8)

    txt_utf8 = "\n".join(txt_lines)
    open(OUT_FILE, "w").write(txt_utf8)

def main():
    extract_articles()
    close_conn()

if __name__ == "__main__":
    main()
