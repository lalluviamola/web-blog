#!/usr/bin/env python
import os.path
import sys
import re
import datetime
import urlparse
import StringIO
import httplib
import traceback
import textile
import postsparse
import util
import pickle
import genkbhtml

SERVER = "http://127.0.0.1:8081/import"
#SERVER = "http://blog2.kowalczyk.info"

SCRIPT_DIR = os.path.dirname(__file__)
SRCDIR = os.path.join(SCRIPT_DIR, "..", "srcblog")
KB_SRC_FILE = os.path.join(SCRIPT_DIR, "..", "srcblog", "knowledge-base.txt")

(POST_TYPE, POST_URL, POST_FORMAT, POST_DATE, POST_BODY, POST_TITLE, POST_TAGS) = ("type", "url", "format", "date", "body", "title", "tags")

def get_content_type(filename):
    return "plain/text"

def gen_base_auth_header_val(user, pwd):
    return ""

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    assert fields or files
    if fields:
        for (key, value) in fields:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"' % key)
            L.append('')
            L.append(value)
    if files:
        for (key, filename, value) in files:
            L.append('--' + BOUNDARY)
            L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            L.append('Content-Type: %s' % get_content_type(filename))
            L.append('')
            L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

# from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/146306
def post_multipart(host, selector, fields, files, username=None, pwd=None):
    """
    Post fields and files to an http host as multipart/form-data.
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return the server's response page.
    """
    #print("post_multipart selector=%s" % selector)
    data = None
    try:
        content_type, body = encode_multipart_formdata(fields, files)
        conn = httplib.HTTPConnection(host)
        conn.putrequest('POST', selector)
        conn.putheader('Content-Type', content_type)
        conn.putheader('Content-Length', str(len(body)))
        if username:
            assert(pwd)
            conn.putheader('Authorization', "Basic %s" % gen_base_auth_header_val(username, pwd))
        conn.endheaders()
        #print "post_multipart() body: '%s'" % body
        conn.send(body)
        resp = conn.getresponse()
        #err = resp.status
        data = resp.read()
    except:
        print "post_multipart failed"
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60
    #print data
    return data

def do_http_post_fields(url, fields, username=None, pwd=None):
    #print("do_http_post_fields url=%s" % url)
    url_parts = urlparse.urlparse(url)
    host = url_parts.netloc
    selector = url_parts.path
    if url_parts.query:
        selector = selector + "?" + url_parts.query
    return post_multipart(host, selector, fields, None, username, pwd)

def upload_post(url, posts):
  fields = [('posts_to_import', posts)]
  do_http_post_fields(url, fields)

def onlyascii(c):
  if c in " _.;,-":
    return c
  if ord(c) < 48 or ord(c) > 127:
    return ''
  else: 
    return c

def urlify(s):
  s = s.strip().lower()
  s = filter(onlyascii, s)
  for c in [" ", "_", "=", ".", ";", ":", "/", "\\", "\"", "'", "(", ")", "{", "}", "?", ","]:
    s = s.replace(c, "-")
  # TODO: a crude way to convert two-or-more consequtive '-' into just one
  # it's really a job for regex
  while True:
    new = s.replace("--", "-")
    if new == s:
      break
    #print "new='%s', prev='%s'" % (new, s)
    s = new
  s = s.strip("-")[:48]
  s = s.strip("-")
  return s

# generate unique, pretty url names for posts. 
def gen_urls(posts):
  all_urls = {}
  for p in posts:
    dateymd = p["date"].split(" ")[0]
    (y,m,d) = dateymd.split("-")
    pretty = urlify(p[POST_TITLE])
    n = 0
    full = "blog/%s/%s/%s/%s.html" % (y,m,d,pretty)
    while full in all_urls:
      n += 1
      full = "blog/%s/%s/%s/%s-%d.html" % (y,m,d,pretty,n)
    all_urls[full] = 1
    p["url"] = full
    #print("'%s' '%s'" % (full,p[POST_TITLE]))
    #print(full)

# from django
def linebreaks(value):
    "Converts newlines into <p> and <br />s"
    value = re.sub(r'\r\n|\r|\n', '\n', value) # normalize newlines
    paras = re.split('\n{2,}', value)
    paras = ['<p>%s</p>' % p.strip().replace('\n', '<br />') for p in paras]
    return '\n\n'.join(paras)

def to_unicode(val):
    if isinstance(val, unicode): return val
    try:
        return unicode(val, 'latin-1')
    except:
        pass
    try:
        return unicode(val, 'ascii')
    except:
        pass
    try:
        return unicode(val, 'utf-8')
    except:
        raise

def to_utf8(val):
    uni = to_unicode(val)
    return uni.encode('utf-8')

def str_to_datetime(val):
    return datetime.datetime.strptime(val, "%Y-%m-%d %H:%M:%S")

def str_kb_to_datetime(val):
    return datetime.datetime.strptime(val, "%Y-%m-%d")

def get_post_raw_content(post):
    filename = post["file"]
    return postsparse.get_blog_post_content(filename)

def get_post_html_content(post):
    filename = post["file"]
    format = post["format"]
    body = postsparse.get_blog_post_content(filename)
    if format == "wphtml":
        body = linebreaks(body)
    elif format == "html":
        # do nothing, leave it as it is
        pass
    elif format == "textile":
        txt = body.encode('utf-8')
        body = textile.textile(txt, encoding='utf-8', output='utf-8')
    else:
        print("Unsupported format: '%s'" % format)
    assert 0
    return body

# converts post to a format that can be sent over the wire to /import url:
# * dates from text to datetime instance
# * body to utf8
# * wphtml format to html
# * strip all unnecessary data
def convert_blog_post(post):
    np = {}
    np[POST_TYPE] = to_utf8("blog")
    np[POST_DATE] = str_to_datetime(post[POST_DATE])
    post[POST_BODY] = get_post_raw_content(post)
    body = post[POST_BODY]
    if post[POST_FORMAT] == "wphtml":
        post[POST_FORMAT] = "html"
        body = linebreaks(body)
    np[POST_BODY] = to_utf8(body)
    for item in [POST_TITLE, POST_FORMAT]:
        np[item] = to_utf8(post[item])
    return np

def convert_kb_article(article):
    np = {}
    np[POST_TYPE] = to_utf8("kb")
    article_date_str = article.dates[0]
    np[POST_DATE] = str_kb_to_datetime(article_date_str)
    np[POST_BODY] = to_utf8(article.get_body())
    np[POST_TITLE] = to_utf8(article.title)
    np[POST_FORMAT] = to_utf8("markdown")
    np[POST_TAGS] = to_utf8(", ".join(article.tags))
    return np

def upload_to_gae(posts):
    fo = StringIO.StringIO()
    pickle.dump(posts, fo)
    pickled = fo.getvalue()
    fo.close()
    upload_post(SERVER, pickled)

def itern(seq, n):
    res = []
    left = n
    for s in seq:
        if left > 0:
            res.append(s)
            left -= 1
        else:
            yield res
            left = n-1
            res = [s]
    if len(res) > 0:
        yield res

def upload_posts(posts):
    MAX_TO_UPLOAD = 100
    for to_upload in itern(posts, 10):
        for p in to_upload:
            url = p[POST_URL]
            format = p[POST_FORMAT]
            date = p[POST_DATE]
            print("uploading %s, %s, %s" % (url, format, date))
        upload_to_gae(to_upload)
        MAX_TO_UPLOAD -= 1
        if MAX_TO_UPLOAD < 1:
            print("Reached max uploads")
            break

def upload_blog():
    if not util.dir_exists(SRCDIR):
        print("Dir '%s' doesn't exist" % SRCDIR)
        sys.exit(1)
    post_files = postsparse.scan_posts(SRCDIR)
    posts = post_files.values()
    posts.sort(lambda x,y: cmp(x[POST_DATE], y[POST_DATE]))
    gen_urls(posts)
    print("posts: %d" % len(posts))
    posts = [convert_blog_post(p) for p in posts]
    upload_posts(posts)

def upload_kb():
    articles = genkbhtml.process_file(KB_SRC_FILE)
    articles = [convert_kb_article(article) for article in articles if not article.is_hidden()]
    print("len(articles)=%d" % len(articles))
    upload_posts(articles)

def main():
    #upload_blog()
    upload_kb()

def main2():
    if not util.dir_exists(SRCDIR):
        print("Dir '%s' doesn't exist" % SRCDIR)
        sys.exit(1)
    post_files = postsparse.scan_posts(SRCDIR)
    posts = post_files.values()
    p = posts[0]
    print(p.keys())

if __name__ == "__main__":
    main()
