# This code is in Public Domain. Take all the code you want, we'll just write more.
import os
import string
import time
import datetime
import re
import StringIO
import pickle
import bz2
import urllib
import cgi
import sha
import traceback
import wsgiref.handlers
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from django.utils import feedgenerator
from django.template import Context, Template
import logging

COMPRESS_PICKLED = False
NO_MEMCACHE = False

# deployed name of the server. Only for redirection from *.appspot.com 
SERVER = "blog.kowalczyk.info"

# memcache key for caching atom.xml
ATOM_MEMCACHE_KEY = "at"
JSON_ADMIN_MEMCACHE_KEY = "jsa"
JSON_NON_ADMIN_MEMCACHE_KEY = "jsna"

# e.g. "http://localhost:8081" or "http://blog.kowalczyk.info"
g_root_url = None

HTTP_NOT_ACCEPTABLE = 406

(POST_DATE, POST_FORMAT, POST_BODY, POST_TITLE, POST_TAGS, POST_URL, POST_PRIVATE) = ("date", "format", "body", "title", "tags", "url", "private")

ALL_FORMATS = (FORMAT_TEXT, FORMAT_HTML, FORMAT_TEXTILE, FORMAT_MARKDOWN) = ("text", "html", "textile", "markdown")

class TextContent(db.Model):
    content = db.TextProperty(required=True)
    published_on = db.DateTimeProperty(auto_now_add=True)
    format = db.StringProperty(required=True,choices=set(ALL_FORMATS))
    # sha1 of content + format
    sha1_digest = db.StringProperty(required=True)

class Article(db.Model):
    permalink = db.StringProperty(required=True)
    # for redirections
    permalink2 = db.StringProperty(required=False)
    is_public = db.BooleanProperty(default=False)
    is_deleted = db.BooleanProperty(default=False)
    title = db.StringProperty()
    # copy of TextContent.content
    body = db.TextProperty(required=True)
    # copy of TextContent.published_on of first version
    published_on = db.DateTimeProperty(auto_now_add=True)
    # copy of TextContent.published_on of last version
    updated_on = db.DateTimeProperty(auto_now_add=True)
    # copy of TextContent.format
    format = db.StringProperty(required=True,choices=set(ALL_FORMATS))
    tags = db.StringListProperty(default=[])
    # points to TextContent
    previous_versions = db.ListProperty(db.Key, default=[])

    def full_permalink(self):
        return g_root_url + '/' + self.permalink
    
    def rfc3339_published_on(self):
        return to_rfc339(self.published_on)

    def rfc3339_updated_on(self):
        return to_rfc339(self.updated_on)

def to_rfc339(dt): return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def to_simple_date(dt): return dt.strftime('%Y-%m-%d')

def httpdate(dt): return dt.strftime('%a, %d %b %Y %H:%M:%S GMT')

def utf8_to_uni(val): return unicode(val, "utf-8")

def encode_code(text):
    for (txt,replacement) in [("&","&amp;"), ("<","&lt;"), (">","&gt;")]:
        text = text.replace(txt, replacement)
    return text

def txt_cookie(txt): return sha.new(txt.encode("utf-8")).hexdigest()

def articles_info_memcache_key():
    if COMPRESS_PICKLED:
        return "akc"
    return "ak"

def clear_memcache():
    memcache.delete(articles_info_memcache_key())
    memcache.delete(ATOM_MEMCACHE_KEY)
    memcache.delete(JSON_ADMIN_MEMCACHE_KEY)
    memcache.delete(JSON_NON_ADMIN_MEMCACHE_KEY)

def build_articles_summary():
    ATTRS_TO_COPY = ["title", "permalink", "published_on", "format", "tags", "is_public", "is_deleted"]
    query = Article.gql('ORDER BY __key__')
    articles = []
    while True:
        got = query.fetch(201)
        logging.info("got %d articles" % len(got))
        for article in got[:200]:
            a = {}
            for attr in ATTRS_TO_COPY:
                a[attr] = getattr(article,attr)
            articles.append(a)
        if len(got) <= 200:
            break
        query = Article.gql('WHERE __key__ > :1 ORDER BY __key__', got[199].key())
    articles.sort(lambda x, y: cmp(y["published_on"], x["published_on"]))
    return articles

def build_articles_json(for_admin):
    import simplejson as json
    ATTRS_TO_COPY = ["title", "permalink", "published_on", "tags", "is_public", "is_deleted"]
    query = Article.gql('ORDER BY __key__')
    articles = []
    while True:
        got = query.fetch(201)
        logging.info("got %d articles" % len(got))
        for article in got[:200]:
            if article.is_deleted or not article.is_public and not for_admin:
                continue
            a = []
            a.append(getattr(article, "published_on"))
            a.append(getattr(article, "permalink"))
            a.append(getattr(article, "title"))
            a.append(getattr(article, "tags"))
            a.append(getattr(article, "is_public"))
            a.append(getattr(article, "is_deleted"))
            articles.append(a)
        if len(got) <= 200:
            break
        query = Article.gql('WHERE __key__ > :1 ORDER BY __key__', got[199].key())
    articles.sort(lambda x, y: cmp(y[0], x[0]))
    for a in articles:
        a[0] = to_simple_date(a[0])
    #json_txt = json.dumps(articles, indent=4) # pretty-printed version
    #json_txt = json.dumps(articles) # regular version
    json_txt = json.dumps(articles, separators=(',',':')) # compact version
    return "var __articles_json = %s; articlesJsonLoaded(__articles_json);" % json_txt

def pickle_data(data):
    fo = StringIO.StringIO()
    pickle.dump(data, fo, pickle.HIGHEST_PROTOCOL)
    pickled_data = fo.getvalue()
    if COMPRESS_PICKLED:
        pickled_data = bz2.compress(pickled_data)
    #fo.close()
    return pickled_data

def unpickle_data(data_pickled):
    if COMPRESS_PICKLED:
        data_pickled = bz2.decompress(data_pickled)
    fo = StringIO.StringIO(data_pickled)
    data = pickle.load(fo)
    fo.close()
    return data

def filter_nonadmin_articles(articles_summary):
    for article_summary in articles_summary:
        if article_summary["is_public"] and not article_summary["is_deleted"]:
            yield article_summary

def filter_deleted_articles(articles_summary):
    for article_summary in articles_summary:
        if not article_summary["is_deleted"]:
            yield article_summary

# not private: not public and not deleted
def filter_nonprivate_articles(articles_summary):
    for article_summary in articles_summary:
        if not article_summary["is_public"] and not article_summary["is_deleted"]:
            yield article_summary

def filter_nondeleted_articles(articles_summary):
    for article_summary in articles_summary:
        if article_summary["is_deleted"]:
            yield article_summary

def filter_by_tag(articles_summary, tag):
    for article_summary in articles_summary:
        if tag in article_summary["tags"]:
            yield article_summary

def new_or_dup_text_content(body, format):
    assert isinstance(body, unicode)
    assert isinstance(format, unicode)
    full = body + format
    sha1_digest = sha.new(full.encode("utf-8")).hexdigest()
    existing = TextContent.gql("WHERE sha1_digest = :1", sha1_digest).get()
    if existing: 
        return (existing, True)
    text_content = TextContent(content=body, format=format, sha1_digest=sha1_digest)
    text_content.put()
    return (text_content, False)

(ARTICLE_SUMMARY_PUBLIC_OR_ADMIN, ARTICLE_PRIVATE, ARTICLE_DELETED) = range(3)

def get_articles_summary(articles_type = ARTICLE_SUMMARY_PUBLIC_OR_ADMIN):
    pickled = memcache.get(articles_info_memcache_key())
    if NO_MEMCACHE: pickled = None
    if pickled:
        articles_summary = unpickle_data(pickled)
        #logging.info("len(articles_summary) = %d" % len(articles_summary))
    else:
        articles_summary = build_articles_summary()
        pickled = pickle_data(articles_summary)
        logging.info("len(articles_pickled) = %d" % len(pickled))
        memcache.set(articles_info_memcache_key(), pickled)
    if articles_type == ARTICLE_SUMMARY_PUBLIC_OR_ADMIN:
        if users.is_current_user_admin():
            articles_summary = filter_deleted_articles(articles_summary)
        else:
            articles_summary = filter_nonadmin_articles(articles_summary)
    elif articles_type == ARTICLE_PRIVATE:
        articles_summary = filter_nonprivate_articles(articles_summary)
    elif articles_type == ARTICLE_DELETED:
        articles_summary = filter_nondeleted_articles(articles_summary)
    return articles_summary

def get_articles_json():
    memcache_key = JSON_NON_ADMIN_MEMCACHE_KEY
    if users.is_current_user_admin():
        memcache_key = JSON_ADMIN_MEMCACHE_KEY
    articles_json = memcache.get(memcache_key)
    if NO_MEMCACHE: articles_json = None
    if not articles_json:
        #logging.info("re-generating articles_json")
        for_admin = users.is_current_user_admin()
        articles_json = build_articles_json(for_admin)
        memcache.set(memcache_key, articles_json)
    else:
        #logging.info("articles_json in cache")
        pass
    sha1 = sha.new(articles_json).hexdigest()
    return (articles_json, sha1)

def get_article_json_url():
    (json, sha1) = get_articles_json()
    return "/js/articles.js?%s" % sha1

def show_analytics(): return not is_localhost()

def jquery_url():
    url = "http://ajax.googleapis.com/ajax/libs/jquery/1.3.1/jquery.min.js"
    if is_localhost(): url = "/static/js/jquery-1.3.1.js"
    return url

def prettify_js_url():
    url = "http://google-code-prettify.googlecode.com/svn-history/r61/trunk/src/prettify.js"
    if is_localhost(): url = "/static/js/prettify.js"
    return url

def prettify_css_url():
    url = "http://google-code-prettify.googlecode.com/svn-history/r61/trunk/src/prettify.css"
    if is_localhost(): url = "/static/js/prettify.css"
    return url

def is_empty_string(s):
    if not s: return True
    s = s.strip()
    return 0 == len(s)

def urlify(title):
    url = re.sub('-+', '-', 
                  re.sub('[^\w-]', '', 
                         re.sub('\s+', '-', title.strip())))
    return url[:48]

def tags_from_string_iter(tags_string):
  for t in tags_string.split(","):
      t = t.strip()
      if t:
          yield t

# given e.g. "a, b  c , ho", returns ["a", "b", "c", "ho"]
def tags_from_string(tags_string):
    return [t for t in tags_from_string_iter(tags_string)]

def checkbox_to_bool(checkbox_val):
    return "on" == checkbox_val

def is_localhost():
    return "://localhost" in g_root_url or "://127.0.0.1" in g_root_url

def remember_root_url(wsgi_app):
    def helper(env, start_response):
        global g_root_url
        g_root_url = env["wsgi.url_scheme"] + "://" + env["HTTP_HOST"]
        return wsgi_app(env, start_response)
    return helper

def redirect_from_appspot(wsgi_app):
    def redirect_if_needed(env, start_response):
        if env["HTTP_HOST"].startswith('kjkblog.appspot.com'):
            import webob, urlparse
            request = webob.Request(env)
            scheme, netloc, path, query, fragment = urlparse.urlsplit(request.url)
            url = urlparse.urlunsplit([scheme, SERVER, path, query, fragment])
            start_response('301 Moved Permanently', [('Location', url)])
            return ["301 Moved Peramanently", "Click Here %s" % url]
        else:
            return wsgi_app(env, start_response)
    return redirect_if_needed

def template_out(response, template_name, template_values = {}):
    response.headers['Content-Type'] = 'text/html'
    #path = os.path.join(os.path.dirname(__file__), template_name)
    path = template_name
    #logging.info("tmpl: %s" % path)
    res = template.render(path, template_values)
    response.out.write(res)

def do_404(response, url):
    response.set_status(404)
    template_out(response, "tmpl/404.html", { "url" : url })

def lang_to_prettify_lang(lang):
    #from http://google-code-prettify.googlecode.com/svn/trunk/README.html
    #"bsh", "c", "cc", "cpp", "cs", "csh", "cyc", "cv", "htm", "html",
    #"java", "js", "m", "mxml", "perl", "pl", "pm", "py", "rb", "sh",
    #"xhtml", "xml", "xsl".
    LANG_TO_PRETTIFY_LANG_MAP = { 
        "c" : "c", 
        "c++" : "cc", 
        "cpp" : "cpp", 
        "python" : "py",
        "html" : "html",
        "xml" : "xml",
        "perl" : "pl",
        "c#" : "cs",
        "javascript" : "js",
        "java" : "java"
    }
    if lang in LANG_TO_PRETTIFY_LANG_MAP:
        return "lang-%s" % LANG_TO_PRETTIFY_LANG_MAP[lang]
    return None

def txt_with_code_parts(txt):
    code_parts = {}
    while True:
        code_start = txt.find("<code", 0)
        if -1 == code_start: break
        lang_start = code_start + len("<code")
        lang_end = txt.find(">", lang_start)
        if -1 == lang_end: break
        code_end_start = txt.find("</code>", lang_end)
        if -1 == code_end_start: break
        code_end_end = code_end_start + len("</code>")
        lang = txt[lang_start:lang_end].strip()
        code = txt[lang_end+1:code_end_start].strip()
        prettify_lang = None
        if lang:
            prettify_lang = lang_to_prettify_lang(lang)
        if prettify_lang:
            new_code = '<pre class="prettyprint %s">\n%s</pre>' % (prettify_lang, encode_code(code))
        else:
            new_code = '<pre class="prettyprint">\n%s</pre>' % encode_code(code)
        new_code_cookie = txt_cookie(new_code)
        assert(new_code_cookie not in code_parts)
        code_parts[new_code_cookie] = new_code
        to_replace = txt[code_start:code_end_end]
        txt = txt.replace(to_replace, new_code_cookie)
    return (txt, code_parts)

def markdown_with_code_to_html(txt):
    from markdown2 import markdown
    (txt, code_parts) = txt_with_code_parts(txt)
    html = markdown(txt)
    for (code_replacement_cookie, code_html) in code_parts.items():
        html = html.replace(code_replacement_cookie, code_html)
    return html

def textile_with_code_to_html(txt):
    from textile import textile
    (txt, code_parts) = txt_with_code_parts(txt)
    txt = txt.encode('utf-8')
    html = textile(txt, encoding='utf-8', output='utf-8')
    html =  unicode(html, 'utf-8')
    for (code_replacement_cookie, code_html) in code_parts.items():
        html = html.replace(code_replacement_cookie, code_html)
    return html

def text_with_code_to_html(txt):
    (txt, code_parts) = txt_with_code_parts(txt)
    html = plaintext2html(txt)
    for (code_replacement_cookie, code_html) in code_parts.items():
        html = html.replace(code_replacement_cookie, code_html)
    return html

# from http://www.djangosnippets.org/snippets/19/
re_string = re.compile(r'(?P<htmlchars>[<&>])|(?P<space>^[ \t]+)|(?P<lineend>\r\n|\r|\n)|(?P<protocal>(^|\s)((http|ftp)://.*?))(\s|$)', re.S|re.M|re.I)
def plaintext2html(text, tabstop=4):
    def do_sub(m):
        c = m.groupdict()
        if c['htmlchars']:
            return cgi.escape(c['htmlchars'])
        if c['lineend']:
            return '<br>'
        elif c['space']:
            t = m.group().replace('\t', '&nbsp;'*tabstop)
            t = t.replace(' ', '&nbsp;')
            return t
        elif c['space'] == '\t':
            return ' '*tabstop;
        else:
            url = m.group('protocal')
            if url.startswith(' '):
                prefix = ' '
                url = url[1:]
            else:
                prefix = ''
            last = m.groups()[-1]
            if last in ['\n', '\r', '\r\n']:
                last = '<br>'
            return '%s<a href="%s">%s</a>%s' % (prefix, url, url, last)
    return re.sub(re_string, do_sub, text)

def gen_html_body(format, txt):
    if format == "textile":
        html = textile_with_code_to_html(txt)
    elif format == "markdown":
        html = markdown_with_code_to_html(txt)
    elif format == "text":
        html = text_with_code_to_html(txt)
    elif format == "html":
        # TODO: code highlighting for html
        html = txt
    return html

def article_gen_html_body(article):
    html = gen_html_body(article.format, article.body)
    article.html_body = html

def do_sitemap_ping():
    if is_localhost(): return
    sitemap_url = "%s/sitemap.xml" % g_root_url
    form_fields = { "sitemap" : sitemap_url }
    urlfetch.fetch(url="http://www.google.com/webmasters/tools/ping",
                   payload=urllib.urlencode(form_fields),
                   method=urlfetch.GET)
    logging.info("Pinged http://www.google.com/webmasters/tools/ping with %s" % sitemap_url)

def find_next_prev_article(article):
    articles_summary = get_articles_summary()
    # TODO: change code below to not require this "materialization"
    # of articles_summary generator
    articles_summary = [a for a in articles_summary]
    permalink = article.permalink
    num = len(articles_summary)
    i = 0
    next = None
    prev = None
    # TODO: could bisect for (possibly) faster search
    while i < num:
        a = articles_summary[i]
        if a["permalink"] == permalink:
            if i > 0:
                next = articles_summary[i-1]
            if i < num-1:
                prev = articles_summary[i+1]
            return (next, prev, i, num)
        i = i + 1
    return (next, prev, i, num)

class NotFoundHandler(webapp.RequestHandler):
    def get(self, url):
        do_404(self.response, url)

def get_login_logut_url(url):
    if users.is_current_user_admin():
        return users.create_logout_url(url)
    else:
        return users.create_login_url(url)

def url_for_tag(tag):
    return '<a href="/tag/%s">%s</a>' % (urllib.quote(tag), tag)

def render_article(response, article):
    full_permalink = g_root_url + "/" + article.permalink
    article_gen_html_body(article)
    (next, prev, article_no, articles_count) = find_next_prev_article(article)
    tags_urls = [url_for_tag(tag) for tag in article.tags]
    vals = {
        'jquery_url' : jquery_url(),
        'articles_js_url' : get_article_json_url(),
        'prettify_js_url' : prettify_js_url(),
        'prettify_css_url' : prettify_css_url(),
        'is_admin' : users.is_current_user_admin(),
        'login_out_url' : get_login_logut_url(full_permalink),
        'article' : article,
        'next_article' : next,
        'prev_article' : prev,
        'show_analytics' : show_analytics(),
        'tags_display' : ", ".join(tags_urls),
        'article_no' : article_no + 1,
        'articles_count' : articles_count,
        'full_permalink' : full_permalink,
    }
    template_out(response, "tmpl/article.html", vals)

# responds to /
class IndexHandler(webapp.RequestHandler):
    def get(self):
        is_admin = users.is_current_user_admin()
        articles_summary = get_articles_summary()
        articles_summary = [a for a in articles_summary]
        articles_count = len(articles_summary)
        articles_summary = articles_summary[:5]
        articles_summary_set_tags_display(articles_summary)
        vals = {
            'jquery_url' : jquery_url(),
            'articles_js_url' : get_article_json_url(),
            'is_admin' : users.is_current_user_admin(),
            'login_out_url' : get_login_logut_url("/"),
            'articles_summary' : articles_summary,
            'articles_count' : articles_count,
            'show_analytics' : show_analytics(),
        }
        template_out(self.response, "tmpl/index.html", vals)

# responds to /tag/${tag}
class TagHandler(webapp.RequestHandler):
    def get(self, tag):
        tag = urllib.unquote(tag)
        logging.info("tag: '%s'" % tag)
        articles_summary = get_articles_summary()
        articles_summary = filter_by_tag(articles_summary, tag)
        do_archives(self.response, articles_summary, tag)

# responds to /js/${url}
class JsHandler(webapp.RequestHandler):
    def get(self, url):
        logging.info("JsHandler, asking for '%s'" % url)
        if url == "articles.js":
            (json_txt, sha1) = get_articles_json()
            # must over-ride Cache-Control (is 'no-cache' by default)
            self.response.headers['Cache-Control'] = 'public, max-age=31536000'
            self.response.headers['Content-Type'] = 'text/plain'
            now = datetime.datetime.now()
            expires_date_txt = httpdate(now + datetime.timedelta(days=365))
            self.response.headers.add_header("Expires", expires_date_txt)
            self.response.out.write(json_txt)

# responds to /article/* and /kb/* and /blog/* (/kb and /blog for redirects
# for links from old website)
class ArticleHandler(webapp.RequestHandler):
    def get(self, url):
        permalink = "article/" + url
        is_admin = users.is_current_user_admin()
        article = Article.gql("WHERE permalink = :1", permalink).get()
        if not article:
            #logging.info("No article with permalink: '%s'" % permalink)
            url = self.request.path_info[1:]
            #logging.info("path: '%s'" % url)
            article = Article.gql("WHERE permalink2 = :1", url).get()
            if article:
                self.redirect(g_root_url + "/" + article.permalink, True)

        if article and not is_admin:
            if article.is_deleted or not article.is_public:
                article = None

        if not article: return do_404(self.response, url)
        render_article(self.response, article)

class PermanentDeleteHandler(webapp.RequestHandler):
    def get(self):
        assert users.is_current_user_admin()
        article_id = self.request.get("article_id")
        article = db.get(db.Key.from_path("Article", int(article_id)))
        # only allow permanent deletion of articles only marked as deleted
        # forcing this two step process is to make sure user doesn't deletes
        # by accident
        assert article.is_deleted
        article.delete()
        clear_memcache()
        logging.info("Permanently deleted article with id %s" % article_id)
        return self.redirect("/app/showdeleted")

class DeleteUndeleteHandler(webapp.RequestHandler):
    def get(self):
        assert users.is_current_user_admin()
        article_id = self.request.get("article_id")
        #logging.info("article_id: '%s'" % article_id)
        article = db.get(db.Key.from_path("Article", int(article_id)))
        assert article

        if article.is_deleted:
            article.is_deleted = False
        else:
            article.is_deleted = True
        article.put()
        clear_memcache()
        url = "/" + article.permalink
        self.redirect(url)

def gen_permalink(title):
    title_sanitized = urlify(title)
    url_base = "article/%s" % (title_sanitized)
    # TODO: maybe use some random number or article.key.id to get
    # to a unique url faster
    iteration = 0
    while iteration < 19:
        if iteration == 0:
            permalink = url_base + ".html"
        else:
            permalink = "%s-%d.html" % (url_base, iteration)
        existing = Article.gql("WHERE permalink = :1", permalink).get()
        if not existing:
            #logging.info("new_permalink: '%s'" % permalink)
            return permalink
        iteration += 1
    return None

def clean_html(html):
    from html2text import html2text
    html = html2text(html)
    assert isinstance(html, unicode)
    return html
    
class ClearMemcacheHandler(webapp.RequestHandler):
    def get(self):
        if not users.is_current_user_admin():
            return self.redirect("/404.html")
        clear_memcache()
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("memcache cleared")

class CleanHtmlHandler(webapp.RequestHandler):

    def post(self):
        html = self.request.get("note")
        html = clean_html(html)
        self.response.headers['Content-Type'] = 'text/html' # does it matter?
        self.response.out.write(html)

class PreviewHandler(webapp.RequestHandler):

    def post(self):
        format = self.request.get("format")
        body = self.request.get("note")
        assert format in ALL_FORMATS
        html = gen_html_body(format, body)
        self.response.headers['Content-Type'] = 'text/html' # does it matter?
        self.response.out.write(html)

class EditHandler(webapp.RequestHandler):

    def create_new_article(self):
        #logging.info("private: '%s'" % self.request.get("private"))
        #logging.info("format: '%s'" % self.request.get("format"))
        #logging.info("title: '%s'" % self.request.get("title"))

        format = self.request.get("format")
        assert format in ALL_FORMATS
        title = self.request.get("title").strip()
        body = self.request.get("note")
        (text_content, is_dup) = new_or_dup_text_content(body, format)
        assert not is_dup

        published_on = text_content.published_on
        permalink = gen_permalink(title)
        assert permalink
        article = Article(permalink=permalink, title=title, body=body, format=format)
        article.is_public = not checkbox_to_bool(self.request.get("private"))
        article.previous_versions = [text_content.key()]
        article.published_on = published_on
        article.updated_on = published_on
        article.tags = tags_from_string(self.request.get("tags"))

        article.put()
        clear_memcache()
        if article.is_public:
            do_sitemap_ping()
        url = "/" + article.permalink
        self.redirect(url)

    def post(self):
        #logging.info("article_id: '%s'" % self.request.get("article_id"))
        #logging.info("format: '%s'" % self.request.get("format"))
        #logging.info("title: '%s'" % self.request.get("title"))
        #logging.info("body: '%s'" % self.request.get("note"))

        if not users.is_current_user_admin():
            return self.redirect("/404.html")

        article_id = self.request.get("article_id")
        if is_empty_string(article_id):
            return self.create_new_article()

        format = self.request.get("format")
        assert format in ALL_FORMATS
        is_public = not checkbox_to_bool(self.request.get("private"))
        update_published_on = checkbox_to_bool(self.request.get("update_published_on"))
        title = self.request.get("title").strip()
        body = self.request.get("note")
        article = db.get(db.Key.from_path("Article", int(article_id)))
        assert article

        tags = tags_from_string(self.request.get("tags"))

        text_content = None
        invalidate_articles_cache = False
        if article.body != body:
            (text_content, is_dup) = new_or_dup_text_content(body, format)
            article.body = body
            #logging.info("updating body")
        else:
            #logging.info("body is the same")
            pass

        if article.title != title:
            new_permalink = gen_permalink(title)
            assert new_permalink
            article.permalink = new_permalink
            invalidate_articles_cache = True

        if text_content:
            article.updated_on = text_content.published_on
        else:
            article.updated_on = datetime.datetime.now()

        if update_published_on:
            article.published_on = article.updated_on
            invalidate_articles_cache = True
    
        if text_content:
            article.previous_versions.append(text_content.key())

        if article.is_public != is_public: invalidate_articles_cache = True
        if article.tags != tags: invalidate_articles_cache = True
            
        article.format = format
        article.title = title
        article.is_public = is_public
        article.tags = tags

        if invalidate_articles_cache: clear_memcache()

        article.put()
        if article.is_public:
            do_sitemap_ping()
        url = "/" + article.permalink
        self.redirect(url)

    def get(self):
        if not users.is_current_user_admin():
            return self.redirect("/404.html")

        article_id = self.request.get('article_id')
        if not article_id:
            vals = {
                'jquery_url' : jquery_url(),
                'format_textile_checked' : "checked",
                'private_checkbox_checked' : "checked",
                'submit_button_text' : "Create new post",
            }
            template_out(self.response, "tmpl/edit.html", vals)
            return

        article = db.get(db.Key.from_path('Article', int(article_id)))
        vals = {
            'jquery_url' : jquery_url(),
            'format_textile_checked' : "",
            'format_markdown_checked' : "",
            'format_html_checked' : "",
            'format_text_checked' : "",
            'update_published_on_checkbox_checked' : "",
            'private_checkbox_checked' : "",
            'article' : article,
            'submit_button_text' : "Update post",            
            'tags' : ", ".join(article.tags),
        }
        vals['format_%s_checked' % article.format] = "checked"
        if not article.is_public:
            vals['private_checkbox_checked'] = "checked"
        template_out(self.response, "tmpl/edit.html", vals)

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

class Year(object):
    def __init__(self, year):
        self.year = year
        self.months = []
    def name(self):
        return self.year
    def add_month(self, month):
        self.months.append(month)

class Month(object):
    def __init__(self, month):
        self.month = month
        self.articles = []
    def name(self):
        return self.month
    def add_article(self, article):
        self.articles.append(article)

def articles_summary_set_tags_display(articles_summary):
    for a in articles_summary:
        tags = a["tags"]
        if tags:
            tags_urls = [url_for_tag(tag) for tag in tags]
            a['tags_display'] = ", ".join(tags_urls)
        else:
            a['tags_display'] = False

# reused by archives and archives-limited-by-tag pages
def do_archives(response, articles_summary, tag_to_display=None):
    curr_year = None
    curr_month = None
    years = []
    posts_count = 0
    for a in articles_summary:
        date = a["published_on"]
        y = date.year
        m = date.month
        a["day"] = date.day
        tags = a["tags"]
        if tags:
            tags_urls = [url_for_tag(tag) for tag in tags]
            a['tags_display'] = ", ".join(tags_urls)
        else:
            a['tags_display'] = False
        monthname = MONTHS[m-1]
        if curr_year is None or curr_year.year != y:
            curr_month = None
            curr_year = Year(y)
            years.append(curr_year)

        if curr_month is None or curr_month.month != monthname:
            curr_month = Month(monthname)
            curr_year.add_month(curr_month)
        curr_month.add_article(a)
        posts_count += 1

    vals = {
        'jquery_url' : jquery_url(),
        'articles_js_url' : get_article_json_url(),
        'years' : years,
        'tag' : tag_to_display,
        'posts_count' : posts_count,
    }
    template_out(response, "tmpl/archive.html", vals)


# responds to /archives.html
class ArchivesHandler(webapp.RequestHandler):
    def get(self):
        articles_summary = get_articles_summary()
        do_archives(self.response, articles_summary)

class SitemapHandler(webapp.RequestHandler):
    def get(self):
        articles = [a for a in get_articles_summary()]
        if not articles:
            return

        for article in articles[:1000]:
            article["full_permalink"] = self.request.host_url + "/" + article["permalink"]
            article["rfc3339_published"] = to_rfc339(article["published_on"])

        self.response.headers['Content-Type'] = 'text/xml'
        vals = { 
            'articles' : articles,
            'root_url' : self.request.host_url,
        }
        template_out(self.response, "tmpl/sitemap.xml", vals)

# responds to /app/articlesjson and /js/
class ArticlesJsonHandler(webapp.RequestHandler):
    def get(self):
        (articles_json, sha1) = get_articles_json()
        #logging.info("len(articles_json)=%d" % len(articles_json))
        vals = { 'json' : articles_json, "articles_js_url" : sha1 }
        template_out(self.response, "tmpl/articlesjson.html", vals)

# responds to /app/showdeleted
class ShowDeletedHandler(webapp.RequestHandler):
    def get(self):
        if not users.is_current_user_admin():
            return self.redirect("/404.html")
        articles_summary = get_articles_summary(ARTICLE_DELETED)
        do_archives(self.response, articles_summary)

# responds to /app/showprivate
class ShowPrivateHandler(webapp.RequestHandler):
    def get(self):
        if not users.is_current_user_admin():
            return self.redirect("/")
        articles_summary = get_articles_summary(ARTICLE_PRIVATE)
        do_archives(self.response, articles_summary)

# responds to /atom.xml
class AtomHandler(webapp.RequestHandler):

    def gen_atom_feed(self):
        feed = feedgenerator.Atom1Feed(
            title = "Krzysztof Kowalczyk blog",
            link = self.request.host_url + "/atom.xml",
            description = "Krzysztof Kowalczyk blog")

        articles = Article.gql("WHERE is_public = True AND is_deleted = False ORDER BY published_on DESC").fetch(25)
        for a in articles:
            title = a.title
            link = self.request.host_url + "/" + a.permalink
            article_gen_html_body(a)
            description = a.html_body
            pubdate = a.published_on
            feed.add_item(title=title, link=link, description=description, pubdate=pubdate)
        feedtxt = feed.writeString('utf-8')
        return feedtxt

    def get(self):
        # TODO: should I compress it?
        feedtxt = memcache.get(ATOM_MEMCACHE_KEY)
        if not feedtxt:
            feedtxt = self.gen_atom_feed()
            memcache.set(ATOM_MEMCACHE_KEY, feedtxt)

        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write(feedtxt)

class SumatraRedirectHandler(webapp.RequestHandler):
    def get(self):
        return self.redirect("/software/sumatrapdf/", True)

class FeedRedirectHandler(webapp.RequestHandler):
    def get(self):
        return self.redirect("/atom.xml", True)

class AddIndexHandler(webapp.RequestHandler):
    def get(self, sub=None):
        return self.redirect(self.request.url + "index.html")

class ForumRedirect(webapp.RequestHandler):
    def get(self, path):
        new_url = "http://forums.fofou.org/sumatrapdf/" + path
        return self.redirect(new_url)

class ForumRssRedirect(webapp.RequestHandler):
    def get(self):
        return self.redirect("http://forums.fofou.org/sumatrapdf/rss", True)

# import one or more articles from old text format
class ImportHandler(webapp.RequestHandler):
    def post(self):
        pickled = self.request.get("posts_to_import")
        if not pickled:
            logging.info("tried to import but no 'posts_to_import' field")
            return self.error(HTTP_NOT_ACCEPTABLE)
        fo = StringIO.StringIO(pickled)
        posts = pickle.load(fo)
        fo.close()
        for post in posts:
            try:
                self.import_post(post)
            except:
                s = traceback.format_exc()
                logging.info(s)

    def import_post(self, post):
        title = utf8_to_uni(post[POST_TITLE])
        published_on = post[POST_DATE]
        permalink = gen_permalink(title)
        assert permalink

        format = utf8_to_uni(post[POST_FORMAT])
        assert format in ALL_FORMATS
        body = post[POST_BODY] # body comes as utf8
        body = utf8_to_uni(body)
        tags = []
        if POST_TAGS in post:
            tags = tags_from_string(post[POST_TAGS])

        (text_content, is_dup) = new_or_dup_text_content(body, format)
        assert not is_dup

        article = Article(permalink=permalink, title=title, body=body, format=format)
        if POST_URL in post:
            article.permalink2 = utf8_to_uni(post[POST_URL])
        article.tags = tags
        article.is_public = True
        if POST_PRIVATE in post and post[POST_PRIVATE]:
            article.is_public = False
        article.previous_versions = [text_content.key()]
        article.published_on = published_on
        article.updated_on = published_on
        article.put()
        logging.info("imported article, url: '%s'" % permalink)

def main():
    mappings = [
        ('/', IndexHandler),
        ('/index.html', IndexHandler),
        ('/archives.html', ArchivesHandler),
        ('/article/(.*)', ArticleHandler),
        # /kb/ and /blog/ are for redirects from old website
        ('/kb/(.*)', ArticleHandler),
        ('/blog/(.*)', ArticleHandler),
        ('/tag/(.*)', TagHandler),
        ('/js/(.*)', JsHandler),
        ('/atom.xml', AtomHandler),
        ('/sitemap.xml', SitemapHandler),
        ('/software/sumatra', SumatraRedirectHandler),
        ('/software/sumatrapdf', SumatraRedirectHandler),
        ('/software/', AddIndexHandler),
        ('/software/(.+)/', AddIndexHandler),
        ('/forum_sumatra/rss.php', ForumRssRedirect),
        ('/forum_sumatra/(.*)', ForumRedirect),
        ('/app/edit', EditHandler),
        ('/app/undelete', DeleteUndeleteHandler),
        ('/app/delete', DeleteUndeleteHandler),
        ('/app/permanentdelete', PermanentDeleteHandler),
        ('/app/showprivate', ShowPrivateHandler),
        ('/app/showdeleted', ShowDeletedHandler),
        #('/app/articlesjson', ArticlesJsonHandler), # for testing
        ('/app/preview', PreviewHandler),
        ('/app/cleanhtml', CleanHtmlHandler),
        ('/app/clearmemcache', ClearMemcacheHandler),
        ('/feed/rss2/atom.xml', FeedRedirectHandler),
        ('/feed/rss2/', FeedRedirectHandler),
        ('/feed/rss2', FeedRedirectHandler),
        ('/feed/', FeedRedirectHandler),
        # only enable /import before importing and disable right
        # after importing, since it's not protected
        #('/import', ImportHandler),
        ('/(.*)', NotFoundHandler)
    ]
    app = webapp.WSGIApplication(mappings,debug=True)
    app = redirect_from_appspot(app)
    app = remember_root_url(app)
    wsgiref.handlers.CGIHandler().run(app)

if __name__ == "__main__":
  main()
