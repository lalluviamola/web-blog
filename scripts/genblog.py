#!/usr/bin/env python
import os.path, sys, re, datetime
import feedgenerator
import postsparse
import util

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(SCRIPT_DIR, ".."))
import textile

SRCDIR = os.path.join(SCRIPT_DIR, "..", "srcblog")

ANALYTICS_TXT = """<script type="text/javascript">
  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', 'UA-194516-1']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(ga);
  })();
</script>
"""

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
"""

CSS_INDEX_TXT = CSS_TXT + """
div#content{margin-top:1.25em;}
#twitterdiv {text-align: center;color:#494949;margin-top:0.75em;}
#twittertxt {font-style: italic;}
#searchbox {margin-top:1.25em;}
a#headsearch { background:transparent url(gfx/search2.png) no-repeat scroll 0 0;
margin:0;padding:5px 0;text-indent:-9999px;width:33px;}
</style>
"""

CSS_TXT += """</style>
"""

CSS_EXT_ARCHIVE_TXT="""<style type="text/css" media="screen">
@import url("css/archive.css");
</style>
"""

ARCHIVE_TEMPLATE = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>Archives {Krzysztof Kowalczyk}</title>
{{css}}
</head>
<body>

<div id="content" style="line-height:1.50">
<h1><a href=index.html>home</a> &#8227; Archives</h1>
<table id=arc>
{{archives}}
</table>
<hr>
<center><a href=index.html>Krzysztof Kowalczyk</a></center>
</div>
{{analytics}}
</body>
</html>
"""

ONE_POST_TEMPLATE = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link rel="alternate" type="application/atom+xml" title="RSS 2.0" href="/atom.xml" />
<title>{{title}}</title>
{{css}}
</head>
<body>

<div id="content">
<h1><a href=../../../../index.html>home</a> &#8227; {{title}}</h1>
{{post}}
<hr>
<center><a href=../../../../index.html>Krzysztof Kowalczyk</a></center>
</div>
{{analytics}}
</body>
</html>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<link rel="alternate" type="application/atom+xml" title="RSS 2.0" href="/atom.xml" />
<title>Krzysztof Kowalczyk weblog</title>
{{css}}

<script>
function $(id) {
	if (document.all)
		return document.all[id];
	if (document.getElementById)
		return document.getElementById(id);
	for (var i=1; i<document.layers.length; i++) {
	    if (document.layers[i].id==id)
	      return document.layers[i];
	}
	return false;
}

String.prototype.linkify = function() {
return this.replace(/[A-Za-z]+:\/\/[A-Za-z0-9-_]+\.[A-Za-z0-9-_:%&\?\/.=]+/g, 
  function(m) {return m.link(m);});
};

function hideEl(id) { $(id).style.display="none"; }
function elIsHidden(id) { return $(id).style.display == "none"; }
function showEl(id) { $(id).style.display="block";}

function toggleEl(id) 
{
    if (elIsHidden(id))
        showEl(id);
    else
        hideEl(id);
}

function toggleSearch() 
{
    toggleEl("searchbox");
    if (!elIsHidden("searchbox"))
        $("searchFieldId").focus();
    $("searchFieldId").value = "";
}

function twitterCallback(twitterData)
{
  var info = twitterData[0];
  var txt = info.text.linkify();
  $("twittertxt").innerHTML = txt;
  showEl("twitterdiv");
}
</script>

</head>
<body>

<div id=head>
  <div id=inner>
  <span class="right"><a href="software/sumatrapdf/">Sumatra PDF</a> &bull; 
  <a href="software/fofou">Fofou</a> &bull; 
  <a href="archives.html">archives</a> &bull; 
  <a href="more.html">more...</a>
  <a id=headsearch href="javascript:toggleSearch();">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</a>
  </span>
  <a href="me.html">Krzysztof Kowalczyk</a>
  </div>
</div>

<div id=searchbox style="display:none;">
<form method="get" action="http://google.com/search">
<input type="hidden" name="IncludeBlogs" value="1">
<input type="hidden" name="as_sitesearch" value="http://blog.kowalczyk.info">

<center><label for="searchFieldId">Search this site:</label> <input type="text" name="q" id="searchFieldId"/>
<input class="button" value="Go" type="submit">
</center>
</form>
</div>

<div id=twitterdiv style="display:none;">
I <a href="http://twitter.com/kjk">twitted</a>: <br><span id=twittertxt></span>
</div>

<div id="content">

<h1><a href={{permalink}}>{{title}}</a></h1>
{{post}}
<hr>
<center><a href=index.html>Krzysztof Kowalczyk</a></center>
</div>
{{analytics}}
<script src="http://twitter.com/statuses/user_timeline/kjk.json?callback=twitterCallback&count=1" type="text/javascript"></script>
</body>
</html>
"""

# generate unique, pretty url names for posts. 
def gen_urls(posts):
  all_urls = {}
  for p in posts:
    dateymd = p["date"].split(" ")[0]
    (y,m,d) = dateymd.split("-")
    pretty = util.urlify(p["title"])
    n = 0
    full = "blog/%s/%s/%s/%s.html" % (y,m,d,pretty)
    while full in all_urls:
      n += 1
      full = "blog/%s/%s/%s/%s-%d.html" % (y,m,d,pretty,n)
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
  util.file_write(feedfile, feedtxt)

def write_index_post(post, filename):
  tmpl = INDEX_TEMPLATE
  body = get_post_html_content(post)
  tmpl = tmpl.replace("{{post}}", body)
  tmpl = tmpl.replace("{{analytics}}", ANALYTICS_TXT)
  tmpl = tmpl.replace("{{css}}", CSS_INDEX_TXT)
  tmpl = tmpl.replace("{{title}}", post["title"])
  tmpl = tmpl.replace("{{permalink}}", post["url"])
  util.file_write_utf8(filename, tmpl)

def write_one_post(post, filename):
  tmpl = ONE_POST_TEMPLATE
  body = get_post_html_content(post)
  tmpl = tmpl.replace("{{post}}", body)
  tmpl = tmpl.replace("{{analytics}}", ANALYTICS_TXT)
  css = CSS_TXT
  tmpl = tmpl.replace("{{css}}", css)
  tmpl = tmpl.replace("{{title}}", post["title"])
  util.file_write_utf8(filename, tmpl)

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
  tmpl = ARCHIVE_TEMPLATE
  tmpl = tmpl.replace("{{archives}}", txt)
  tmpl = tmpl.replace("{{analytics}}", ANALYTICS_TXT)
  css = CSS_TXT
  #css = CSS_EXT_ARCHIVE_TXT
  tmpl = tmpl.replace("{{css}}", css)
  filename = os.path.join("..", "www", "archives.html")
  util.file_write_utf8(filename, tmpl)
  
def main():
  if not util.dir_exists(SRCDIR):
    print("Dir '%s' doesn't exist" % SRCDIR)
    sys.exit(1)
  post_files = postsparse.scan_posts(SRCDIR)
  posts = post_files.values()
  posts.sort(lambda x,y: cmp(x["date"], y["date"]))
  gen_urls(posts)
  print("posts: %d" % len(posts))
  write_feed(posts)
  for p in posts:
    url = p["url"]
    urlparts = url.split("/")
    filename = os.path.join("..", "www", *urlparts)
    write_one_post(p, filename)
  latest = posts[-1]
  filename = os.path.join("..", "www", "index.html")
  write_index_post(latest, filename)
  # should be done last since it reverses posts
  write_archives(posts)
  #print latest

if __name__ == "__main__":
  main()
