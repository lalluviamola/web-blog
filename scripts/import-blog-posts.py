#!/usr/bin/env python

import sys, os.path, sqlite3
import postsparse
import genblog

_g_script_dir = None
def script_dir():
    global _g_script_dir
    if _g_script_dir is None:
        _g_script_dir = os.path.dirname(os.path.realpath(__file__))
    return _g_script_dir

def db_dir():
    return script_dir()

def db_path():
    return os.path.join(db_dir(), "blog.db")

def posts_dir():
    return os.path.join(script_dir(), "..", "srcblog")

CREATE_DB_1_SQL = """
-- immutable piece of content (text). The actual content is stored in a file
-- whose name is equal to sha1 of the content.
-- a piece of content is one of revisions of the posts in posts table
CREATE TABLE content (
      id INTEGER PRIMARY KEY AUTOINCREMENT
    , creation_date TEXT
    -- sha1 of the content and the name of the file that has the actual content
    , sha1 TEXT
    -- refers to posts.id
    , post_id INTEGER
);
"""

CREATE_DB_2_SQL = """
CREATE TABLE posts (
      id INTEGER PRIMARY KEY AUTOINCREMENT 
    -- refers to content.id
    , content_id INTEGER
    , title TEXT
    -- cached content.sha1 from content table
    , last_rev_sha1 TEXT NOT NULL
    -- cached content.creation_date from content table
    , last_rev_date TEXT NOT NULL
);
"""

# This is for one-time only import, so assume that if the database file exists
# we've already imported the posts
def init_db():
    dbpath = db_path()
    if os.path.exists(dbpath):
        print("Database '%s' already exists!" % dbpath)
        sys.exit(1)
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    c.execute(CREATE_DB_1_SQL)
    c.execute(CREATE_DB_2_SQL)
    conn.commit()
    c.close()

def import_posts():
    post_files = postsparse.scan_posts(posts_dir())
    posts = post_files.values()
    posts.sort(lambda x,y: cmp(x["date"], y["date"]))    
    genblog.gen_urls(posts)
    for p in posts:
        url = p["url"];
        print("url: %s" % url)

def main():
    #init_db()
    import_posts()

if __name__ == "__main__":
    main()
