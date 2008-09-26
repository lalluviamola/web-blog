#!/usr/bin/env python

import sys, os.path, sqlite3
import postsparse

# Directory
g_db_dir = None
g_db_path = None

def db_path():
    return os.path.join(g_db_dir, "blog.db")

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
    path = db_path()
    if os.path.exists(path):
        print("Database '%s' already exists!" % path)
        sys.exit(1)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute(CREATE_DB_1_SQL)
    c.execute(CREATE_DB_2_SQL)
    conn.commit()
    c.close()

def calc_dirs():
    global g_db_dir
    g_db_dir = os.path.dirname(os.path.realpath(__file__))
    print("g_db_dir = '%s'" % g_db_dir)

def main():
    calc_dirs()
    init_db()

if __name__ == "__main__":
    main()
