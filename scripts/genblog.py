#!/usr/bin/env python
import random, os.path, sys, codecs, re, datetime
import feedgenerator

SRCDIR = os.path.join("..", "srcblog")

ANALYTICS_TXT = """<script type="text/javascript">
var gaJsHost = (("https:" == document.location.protocol) ? "https://ssl." : "http://www.");
document.write(unescape("%3Cscript src='" + gaJsHost + "google-analytics.com/ga.js' type='text/javascript'%3E%3C/script%3E"));
</script>
<script type="text/javascript">
var pageTracker = _gat._getTracker("UA-194516-1");
pageTracker._initData();
pageTracker._trackPageview();
</script>"""

CSS_TXT = """<style type=text/css>
body{margin:0}
h1,h2,h3{font-size:medium}
h1 a{color:inherit !important;}
img{border:0}
div#head{margin:0;width:100%;font-family:"Lucida Grande",Lucida,Verdana,sans-serif;font-size:small;background:#7f7f7f;color: #fff;padding-top:6px;padding-bottom:6px;font-weight:bold}
div#head div#inner{margin:0 auto;width:600px;}
div#head a {color: #fff;text-decoration: none;}
div#head span.right {float:right;color:#b9b9b9;}
div#content{font:normal medium 'Goudy Bookletter 1911','Gentium Basic','Liberation Serif','Hoefler Text','Goudy Old Style',Cambria,Georgia,serif;margin:1.75em auto;width:600px;line-height:1.25;word-spacing:0.1em}
#arc th{padding:0 1.75em 0 0;vertical-align:baseline;text-align:right}
#arc{border-collapse:collapse;width:100%}
.year th{background:papayawhip;color:black}
</style>
"""

CSS_EXT_POST_TXT="""<style type="text/css" media="screen">
@import url("../../css/kjk.css");
</style>
"""

CSS_EXT_IDX_TXT="""<style type="text/css" media="screen">
@import url("../../css/kjk.css");
</style>
"""

CSS_EXT_ARCHIVE_TXT="""<style type="text/css" media="screen">
@import url("css/archive.css");
</style>
"""
def dir_exists(path): return os.path.exists(path) and os.path.isdir(path)

def make_dir(path):
    if not dir_exists(path): os.makedirs(path)

def file_read_utf8(filename):
  fo = codecs.open(filename, encoding='utf-8', mode="r")
  txt = fo.read()
  fo.close()
  return txt

def file_write_utf8(filename, txt):
  make_dir(os.path.dirname(filename))
  fo = codecs.open(filename, encoding='utf-8', mode="w")
  fo.write(txt)
  fo.close()

def file_write(filename, txt):
  make_dir(os.path.dirname(filename))
  fo = open(filename, mode="wb")
  fo.write(txt)
  fo.close()

def parse_blog_post_headers(post_path):
  vals = {}
  fo = codecs.open(post_path, encoding='utf-8', mode="r")
  for l in fo:
    l = l.strip()
    if not l:
      break
    if ": " not in l:
      print("Invalid line:\n'%s'\n" % l)
    (name, val) = l.split(": ", 1)
    name = name.lower()
    vals[name] = val
  fo.close()
  return vals

def get_blog_post_content(post_path):
  vals = {}
  fo = codecs.open(post_path, encoding='utf-8', mode="r")
  # skip headers
  for l in fo:
    l = l.strip()
    if not l:
      break
  # the rest is post body  
  lines = [l for l in fo]
  fo.close()
  return "".join(lines)

def scan_posts(path):
  def callback(allfiles, dirname, fnames):
    if ".svn" in dirname: return
    if ".git" in dirname: return
    for fname in fnames:
      if "knowledge-base.txt" in fname:
        continue
      if fname.endswith(".txt"):
        #print("dir: %s, file: %s" % (dirname, fname))
        filepath = os.path.join(dirname, fname)
        vals = parse_blog_post_headers(filepath)
        vals["file"] = filepath
        allfiles[filepath] = vals
        #print vals

  allfiles = {}
  os.path.walk(path, callback, allfiles)
  return allfiles

def onlyascii(c):
  if c in " _.;,-":
    return c
  if ord(c) < 48 or ord(c) > 127:
    return ''
  else: 
    return c

# generate unique, pretty url names for posts. 
def gen_urls(posts):
  all_urls = {}
  for p in posts:
    (y,m) = p["date"].split("-",2)[:2]
    pretty = p["title"].strip()
    pretty = pretty.lower()
    pretty = filter(onlyascii, pretty)
    for c in [" ", "_", ".", ";", ":", "/", "\\", "\"", "'", "(", ")", "?"]:
      pretty = pretty.replace(c, "-")
    while True:
      new = pretty.replace("--", "-")
      if new == pretty:
        break
      #print "new='%s', prev='%s'" % (new, pretty)
      pretty = new
    pretty = pretty.strip("-")
    pretty = pretty[:48]
    pretty = pretty.strip("-")
    n = 0
    full = "%s/%s/%s.html" % (y,m,pretty)
    while full in all_urls:
      n += 1
      full = "%s/%s/%s-%d.html" % (y,m,pretty,n)
    all_urls[full] = 1
    p["url"] = full
    #print("'%s' '%s'" % (full,p["title"]))
    #print(full)

# from django
def linebreaks(value):
    "Converts newlines into <p> and <br />s"
    value = re.sub(r'\r\n|\r|\n', '\n', value) # normalize newlines
    paras = re.split('\n{2,}', value)
    paras = ['<p>%s</p>' % p.strip().replace('\n', '<br />') for p in paras]
    return '\n\n'.join(paras)

def get_post_raw_content(post):
  filename = post["file"]
  return get_blog_post_content(filename)

def get_post_html_content(post):
  filename = post["file"]
  body = get_blog_post_content(filename)
  if post["format"] == "wphtml":
    body = linebreaks(body)
  return body

def atom_feed(posts):
  feed = feedgenerator.Atom1Feed(
    title = "Krzysztof Kowalczyk blog",
    link = "http://blog.kowalczyk.info/feed/",
    description = "Krzysztof Kowalczyk blog")

  posts = posts[-25:]
  posts.reverse()
  for p in posts:
    title = p["title"]
    link = "http://blog.kowalczyk.info/" + p["url"]
    description = get_post_html_content(p)
    pubdate = datetime.datetime.strptime(p["date"], "%Y-%m-%d %H:%M:%S")
    feed.add_item(title=title, link=link, description=description, pubdate=pubdate)
  return feed

def write_feed(posts):
  feedfile = os.path.join("..", "www", "atom.xml")
  feed = atom_feed(posts)
  feedtxt = feed.writeString("utf-8")
  #fo = codecs.open(feedfile, encoding='utf-8', mode="w")
  #feed.write(fo, "utf-8")
  #fo.close()
  file_write(feedfile, feedtxt)

def write_index_post(post, filename):
  tmpl = file_read_utf8("index_template.html")
  body = get_post_html_content(post)
  tmpl = tmpl.replace("{{post}}", body)
  tmpl = tmpl.replace("{{analytics}}", ANALYTICS_TXT)
  css = CSS_TXT
  #css = CSS_EXT_IDX_TXT
  tmpl = tmpl.replace("{{css}}", css)
  tmpl = tmpl.replace("{{title}}", post["title"])
  tmpl = tmpl.replace("{{permalink}}", post["url"])
  file_write_utf8(filename, tmpl)

def write_one_post(post, filename):
  tmpl = file_read_utf8("one_template.html")
  body = get_post_html_content(post)
  tmpl = tmpl.replace("{{post}}", body)
  tmpl = tmpl.replace("{{analytics}}", ANALYTICS_TXT)
  css = CSS_TXT
  #css = CSS_EXT_POST_TXT
  tmpl = tmpl.replace("{{css}}", css)
  tmpl = tmpl.replace("{{title}}", post["title"])
  file_write_utf8(filename, tmpl)

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def write_archives(posts):
  prevyear = prevmonth = None
  lines = []
  posts.reverse()
  for p in posts:
    url = p["url"]
    title = p["title"]
    date = datetime.datetime.strptime(p["date"], "%Y-%m-%d %H:%M:%S")
    y = date.year
    m = date.month
    day = date.day
    if y != prevyear:
      prevyear = y
      lines.append("<tr class=year><th colspan=2>%d</th></tr>" % y)
    if m != prevmonth:
      prevmonth = m
      monthname = MONTHS[m-1]
      lines.append(u"<tr><th>%s</th><td></td></tr>" % monthname)
    lines.append(u"<tr><th>%d</th><td><a href=%s>%s</a></td></tr>" % (day, url, title))
  txt = "\n".join(lines)
  tmpl = file_read_utf8("archive_template.html")
  tmpl = tmpl.replace("{{archives}}", txt)
  tmpl = tmpl.replace("{{analytics}}", ANALYTICS_TXT)
  css = CSS_TXT
  #css = CSS_EXT_ARCHIVE_TXT
  tmpl = tmpl.replace("{{css}}", css)
  filename = os.path.join("..", "www", "archives.html")
  file_write_utf8(filename, tmpl)
  
def main():
  if not dir_exists(SRCDIR):
    print("Dir '%s' doesn't exist" % SRCDIR)
    sys.exit(1)
  post_files = scan_posts(SRCDIR)
  posts = post_files.values()
  posts.sort(lambda x,y: cmp(x["date"], y["date"]))
  gen_urls(posts)
  print("posts: %d" % len(posts))
  write_feed(posts)
  for p in posts:
    url = p["url"]
    (y,m,name) = url.split("/")
    filename = os.path.join("..", "www", y, m, name)
    write_one_post(p, filename)
  latest = posts[-1]
  filename = os.path.join("..", "www", "index.html")
  write_index_post(latest, filename)
  # should be done last since it reverses posts
  write_archives(posts)
  #print latest

if __name__ == "__main__":
  main()
