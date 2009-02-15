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
import md5
import textile
import markdown2
import cgi
import wsgiref.handlers
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from django.utils import feedgenerator
from django.template import Context, Template
import logging

COMPRESS_PICKLED = True

#DONT_MEMCACHE_ARTICLES = True
DONT_MEMCACHE_ARTICLES = False

#BLOG_URL = "blog.kowalczyk.info"
BLOG_URL = "blog2.kowalczyk.info"

# HTTP codes
HTTP_NOT_ACCEPTABLE = 406
HTTP_NOT_FOUND = 404

(POST_DATE, POST_FORMAT, POST_BODY, POST_TITLE, POST_TAGS) = ("date", "format", "body", "title", "tags")

ALL_FORMATS = (FORMAT_TEXT, FORMAT_HTML, FORMAT_TEXTILE, FORMAT_MARKDOWN) = ("text", "html", "textile", "markdown")

class TextContent(db.Model):
    content = db.TextProperty(required=True)
    published_on = db.DateTimeProperty(auto_now_add=True)
    format = db.StringProperty(required=True,choices=set(ALL_FORMATS))

class Article(db.Model):
    permalink = db.StringProperty(required=True)
    is_public = db.BooleanProperty(default=False)
    is_draft = db.BooleanProperty(default=False)
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

    def rfc3339_published_on(self):
        return self.published_on.strftime('%Y-%m-%dT%H:%M:%SZ')

    def rfc3339_updated_on(self):
        return self.updated_on.strftime('%Y-%m-%dT%H:%M:%SZ')

def encode_code(text):
    for (txt,replacement) in [("&","&amp;"), ("<","&lt;"), (">","&gt;")]:
        text = text.replace(txt, replacement)
    return text

def txt_cookie(txt):
    txt_md5 = md5.new(txt)
    return txt_md5.hexdigest()

def articles_info_memcache_key():
    if COMPRESS_PICKLED:
        return "akc"
    return "ak"

def build_articles_summary():
    articlesq = db.GqlQuery("SELECT * FROM Article ORDER BY published_on DESC")
    articles = []
    for article in articlesq:
        a = { "key_id" : article.key().id() }
        for attr in ["permalink", "is_public", "title", "published_on", "format", "is_draft", "is_deleted", "tags"]:
            a[attr] = getattr(article,attr)
        articles.append(a)
    return articles

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
        if article_summary["is_public"] and not article_summary["is_draft"] and not article_summary["is_deleted"]:
            yield article_summary

def filter_non_draft_non_deleted_articles(articles_summary):
    for article_summary in articles_summary:
        if article_summary["is_draft"] or article_summary["is_deleted"]:
            yield article_summary

def filter_by_tag(articles_summary, tag):
    for article_summary in articles_summary:
        if tag in article_summary["tags"]:
            yield article_summary

(ARTICLE_SUMMARY_PUBLIC_OR_ADMIN, ARTICLE_SUMMARY_DRAFT_AND_DELETED) = range(2)

def get_articles_summary(articles_type = ARTICLE_SUMMARY_PUBLIC_OR_ADMIN):
    articles_pickled = memcache.get(articles_info_memcache_key())
    if DONT_MEMCACHE_ARTICLES: articles_pickled = None
    if articles_pickled:
        articles_summary = unpickle_data(articles_pickled)
        #logging.info("len(articles_summary) = %d" % len(articles_summary))
    else:
        articles_summary = build_articles_summary()
        articles_pickled = pickle_data(articles_summary)
        logging.info("len(articles_pickled) = %d" % len(articles_pickled))
        memcache.set(articles_info_memcache_key(), articles_pickled)
    if articles_type == ARTICLE_SUMMARY_PUBLIC_OR_ADMIN:
        if not users.is_current_user_admin():
            articles_summary = filter_nonadmin_articles(articles_summary)
    elif articles_type == ARTICLE_SUMMARY_DRAFT_AND_DELETED:
        articles_summary = filter_non_draft_non_deleted_articles(articles_summary)
    return articles_summary

g_is_localhost = True

def is_localhost():
    return g_is_localhost

def show_analytics(): return not is_localhost()

def jquery_url():
    url = "http://ajax.googleapis.com/ajax/libs/jquery/1.3.1/jquery.min.js"
    if is_localhost():
        url = "/js/jquery-1.3.1.js"
    return url

def dectect_localhost(wsgi_app):
    def check_if_localhost(env, start_response):
        global g_is_localhost
        host = env["HTTP_HOST"]
        g_is_localhost = host.startswith("localhost") or host.startswith("127.0.0.1")
        return wsgi_app(env, start_response)
    return check_if_localhost

def redirect_from_appspot(wsgi_app):
    def redirect_if_needed(env, start_response):
        if env["HTTP_HOST"].startswith('kjkblog.appspot.com'):
            import webob, urlparse
            request = webob.Request(env)
            scheme, netloc, path, query, fragment = urlparse.urlsplit(request.url)
            url = urlparse.urlunsplit([scheme, BLOG_URL, path, query, fragment])
            start_response('301 Moved Permanently', [('Location', url)])
            return ["301 Moved Peramanently",
                  "Click Here" % url]
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

def markdown(txt): return markdown2.markdown(txt)

def markdown_with_code_to_html(txt):
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
        #print("-------------\n'%s'\n--------------" % code)
        prettify_lang = None
        if lang:
            #print("lang=%s" % lang)
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

    html = markdown(txt)
    has_code = False
    for (code_replacement_cookie, code_html) in code_parts.items():
        html = html.replace(code_replacement_cookie, code_html)
        has_code = True
    return (html, has_code)

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

def article_gen_html_body(article):
    if article.format == "textile":
        txt = article.body.encode('utf-8')
        body = textile.textile(txt, encoding='utf-8', output='utf-8')
        body =  unicode(body, 'utf-8')
        article.html_body = body
    elif article.format == "markdown":
        txt = article.body.encode('utf-8')
        (body, has_code) = markdown_with_code_to_html(txt)
        article.html_body = body
    elif article.format == "text":
        article.html_body = plaintext2html(article.body)
    elif article.format == "html":
        article.html_body = article.body

def find_next_prev_article(article):
    articles_summary = get_articles_summary()
    # TODO: change code below to not require this "materialization"
    # of articles_summary generator
    articles_summary = [a for a in articles_summary]
    key_id = article.key().id()
    num = len(articles_summary)
    i = 0
    next = None
    prev = None
    # TODO: could bisect for (possibly) faster search
    while i < num:
        a = articles_summary[i]
        if a["key_id"] == key_id:
            if i > 0:
                next = articles_summary[i-1]
            if i < num-1:
                prev = articles_summary[i+1]
            return (next, prev)
        i = i + 1
    return (next, prev)

# responds to /
# TODO: combine this with ArticleHandler
class IndexHandler(webapp.RequestHandler):
    def get(self):
        is_admin = users.is_current_user_admin()
        if is_admin:
            article = db.GqlQuery("SELECT * FROM Article ORDER BY published_on DESC").get()
        else:
            article = db.GqlQuery("SELECT * FROM Article WHERE is_public = True AND is_draft = False AND is_deleted = False ORDER BY published_on DESC").get()
        if not article:
            vals = { "url" : "/" }
            template_out(self.response, "tmpl/404.html", vals)
            return

        if is_admin:
            login_out_url = users.create_logout_url("/")
        else:
            login_out_url = users.create_login_url("/")

        article_gen_html_body(article)
        (next, prev) = find_next_prev_article(article)
        tags_urls = ['<a href="/tag/%s">%s</a>' % (tag, tag) for tag in article.tags]
        vals = { 
            'jquery_url' : jquery_url(),
            'is_admin' : is_admin,
            'login_out_url' : login_out_url,
            'article' : article,
            'next_article' : next,
            'prev_article' : prev,
            'show_analytics' : show_analytics(),
            'tags_display' : ", ".join(tags_urls),
            'index_page' : True,
        }
        template_out(self.response, "tmpl/article.html", vals)

# responds to /tag/*
class TagHandler(webapp.RequestHandler):
    def get(self, tag):
        tag = urllib.unquote(tag)
        logging.info("tag: '%s'" % tag)
        articles_summary = get_articles_summary()
        articles_summary = filter_by_tag(articles_summary, tag)
        do_archives(self.response, articles_summary, tag)

# responds to /article/*
class ArticleHandler(webapp.RequestHandler):
    def get(self,url):
        permalink = "article/" + url
        is_admin = users.is_current_user_admin()
        if is_admin:
            article = Article.gql("WHERE permalink = :1", permalink).get()
        else:
            article = Article.gql("WHERE permalink = :1 AND is_public = True AND is_draft = FALSE AND is_deleted = False", permalink).get()
        if not article:
            vals = { "url" : permalink }
            template_out(self.response, "tmpl/404.html", vals)
            return
        article_gen_html_body(article)
        (next, prev) = find_next_prev_article(article)
        tags_urls = ['<a href="/tag/%s">%s</a>' % (tag, tag) for tag in article.tags]
        vals = { 
            'jquery_url' : jquery_url(),
            'is_admin' : is_admin,
            'article' : article,
            'next_article' : next,
            'prev_article' : prev,
            'show_analytics' : show_analytics(),
            'tags_display' : ", ".join(tags_urls),
            'index_page' : False,
        }
        template_out(self.response, "tmpl/article.html", vals)

def is_empty_string(s):
    if not s: return True
    s = s.strip()
    return 0 == len(s)

def urlify(title):
    url = re.sub('-+', '-', 
                  re.sub('[^\w-]', '', 
                         re.sub('\s+', '-', title.strip())))
    return url[:48]

class DeleteUndeleteHandler(webapp.RequestHandler):
    def get(self):
        if not users.is_current_user_admin():
            return self.redirect("/")
        article_id = self.request.get("article_id")
        logging.info("article_id: '%s'" % article_id)
        article = db.get(db.Key.from_path("Article", int(article_id)))
        if not article:
            vals = { "url" : article_id }
            return template_out(self.response, "tmpl/404.html", vals)
        if article.is_deleted:
            article.is_deleted = False
        else:
            article.is_deleted = True
        article.put()
        memcache.delete(articles_info_memcache_key())
        url = "/" + article.permalink
        self.redirect(url)

def iter_split_by(txt, splitter):
    for t in txt.split(splitter):
        t = t.strip()
        if t:
            yield t

def article_tags_from_string_iter(tags_string):
    for a in iter_split_by(tags_string, ","):
        for b in iter_split_by(a, " "):
            yield b

# given e.g. "a, b  c , ho", returns ["a", "b", "c", "ho"]
def article_tags_from_string(tags_string):
    return [t for t in article_tags_from_string_iter(tags_string)]

def checkbox_to_bool(checkbox_val):
    return "on" == checkbox_val

def gen_permalink(title, date, allow_dups = True):
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
        if existing and not allow_dups:
            return None
        if not existing:
            #logging.info("new_permalink: '%s'" % permalink)
            return permalink
        iteration += 1
    return None

class EditHandler(webapp.RequestHandler):

    def create_new_article(self):
        #logging.info("private: '%s'" % self.request.get("private"))
        #logging.info("format: '%s'" % self.request.get("format"))
        #logging.info("title: '%s'" % self.request.get("title"))

        format = self.request.get("format")
        assert format in ALL_FORMATS
        title = self.request.get("title").strip()
        body = self.request.get("note")
        text_content = self.create_new_text_content(body, format)

        published_on = text_content.published_on
        permalink = gen_permalink(title, published_on)
        article = Article(permalink=permalink, title=title, body=body, format=format)
        article.is_public = not checkbox_to_bool(self.request.get("private"))
        article.previous_versions = [text_content.key()]
        article.published_on = published_on
        article.updated_on = published_on
        article.tags = article_tags_from_string(self.request.get("tags"))

        article.put()
        memcache.delete(articles_info_memcache_key())
        # show newly updated article
        url = "/" + article.permalink
        self.redirect(url)

    def create_new_text_content(self, content, format):
        content = TextContent(content=content, format=format)
        content.put()
        return content

    def post(self):
        article_id = self.request.get("article_id")
        logging.info("article_id: '%s'" % article_id)
        if is_empty_string(article_id):
            return self.create_new_article()
        format = self.request.get("format")
        logging.info("format: '%s'" % format)
        # TODO: validate format
        is_public = not checkbox_to_bool(self.request.get("private"))
        is_draft = checkbox_to_bool(self.request.get("draft"))
        title = self.request.get("title").strip()
        logging.info("title: '%s'" % title)
        body = self.request.get("note")
        #logging.info("body: '%s'" % body)
        article = db.get(db.Key.from_path("Article", int(article_id)))
        if not article:
            vals = { "url" : article_id }
            template_out(self.response, "tmpl/404.html", vals)
            return
        tags = article_tags_from_string(self.request.get("tags"))

        text_content = None
        invalidate_articles_cache = False
        if article.body != body:
            text_content = self.create_new_text_content(body, format)
            article.body = body
            logging.info("updating body")
        else:
            logging.info("body is the same")

        if article.title != title:
            new_permalink = gen_permalink(title, article.published_on)
            article.permalink = new_permalink
            invalidate_articles_cache = True

        if text_content:
            article.updated_on = text_content.published_on
        else:
            article.updated_on = datetime.datetime.now()

        if text_content:
            article.previous_versions.append(text_content.key())

        if article.is_public != is_public: invalidate_articles_cache = True
        if article.is_draft != is_draft: invalidate_articles_cache = True
        if article.tags != tags: invalidate_articles_cache = True
            
        article.format = format
        article.title = title
        article.is_public = is_public
        article.is_draft = is_draft
        article.tags = tags

        if invalidate_articles_cache:
            memcache.delete(articles_info_memcache_key())

        article.put()
        url = "/" + article.permalink
        self.redirect(url)

    def get(self):
        article_id = self.request.get('article_id')
        if not article_id:
            vals = {
                'jquery_url' : jquery_url(),
                'format_textile_checked' : "checked",
                'private_checkbox_checked' : "checked",
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
            'private_checkbox_checked' : "",
            'draft_checkbox_checked' : "",
            'article' : article,
            'tags' : ", ".join(article.tags),
        }
        vals['format_%s_checked' % article.format] = "checked"
        if article.is_draft:
            vals['draft_checkbox_checked'] = "checked"
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
            tags_urls = ['<a href="/tag/%s">%s</a>' % (tag, tag) for tag in tags]
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
        'years' : years,
        'is_admin' : users.is_current_user_admin(),
        'tag' : tag_to_display,
        'posts_count' : posts_count,
    }
    template_out(response, "tmpl/archive.html", vals)

# responds to /archives.html
class ArchivesHandler(webapp.RequestHandler):
    def get(self):
        articles_summary = get_articles_summary()
        do_archives(self.response, articles_summary)

class DraftsAndDeletedHandler(webapp.RequestHandler):
    def get(self):
        if not users.is_current_user_admin():
            return self.redirect("/")
        articles_summary = get_articles_summary(ARTICLE_SUMMARY_DRAFT_AND_DELETED)
        curr_year = None
        curr_month = None
        years = []
        for a in articles_summary:
            date = a["published_on"]
            y = date.year
            m = date.month
            a["day"] = date.day
            monthname = MONTHS[m-1]
            if curr_year is None or curr_year.year != y:
                curr_month = None
                curr_year = Year(y)
                years.append(curr_year)

            if curr_month is None or curr_month.month != monthname:
                curr_month = Month(monthname)
                curr_year.add_month(curr_month)
            curr_month.add_article(a)
        vals = {
            'years' : years,
            'is_admin' : users.is_current_user_admin(),
        }
        template_out(self.response, "tmpl/archive.html", vals)

class AtomHandler(webapp.RequestHandler):
    def get(self):
        # TODO: memcache this if turns out to be done frequently
        feed = feedgenerator.Atom1Feed(
            title = "Krzysztof Kowalczyk blog",
            link = "http://blog.kowalczyk.info/feed/",
            description = "Krzysztof Kowalczyk blog")

        articlesq = db.GqlQuery("SELECT * FROM Article WHERE is_public = True AND is_draft = False AND is_deleted = False ORDER BY published_on DESC")
        articles = []
        max_articles = 25
        for a in articlesq:
            max_articles -= 1
            if max_articles < 0:
                break
            articles.append(a)
        for a in articles:
            title = a.title
            link = "http://blog.kowalczyk.info/" + a.permalink
            article_gen_html_body(a)
            description = a.html_body
            pubdate = a.published_on
            feed.add_item(title=title, link=link, description=description, pubdate=pubdate)
        feedtxt = feed.writeString('utf-8')
        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write(feedtxt)
    
class AddIndexHandler(webapp.RequestHandler):
    def get(self, sub=None):
        return self.redirect(self.request.url + "index.html")

class ForumRedirect(webapp.RequestHandler):
    def get(self, path):
        new_url = "http://forums.fofou.org/sumatrapdf/" + path
        return self.redirect(new_url)

class ForumRssRedirect(webapp.RequestHandler):
    def get(self):
        return self.redirect("http://forums.fofou.org/sumatrapdf/rss")

def uni_to_utf8(val): return unicode(val, "utf-8")
 
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
            self.import_post(post)

    def import_post(self, post):
        title = uni_to_utf8(post[POST_TITLE])
        published_on = post[POST_DATE]
        permalink = gen_permalink(title, published_on, allow_dups = False)
        if not permalink:
            logging.info("post for title '%s' already exists" % title)
            return
        format = uni_to_utf8(post[POST_FORMAT])
        assert format in ALL_FORMATS
        body = post[POST_BODY] # body comes as utf8
        body = uni_to_utf8(body)
        tags = []
        if POST_TAGS in post:
            tags = article_tags_from_string(post[POST_TAGS])
        text_content = TextContent(content=body, published_on=published_on, format=format)
        text_content.put()
        article = Article(permalink=permalink, title=title, body=body, format=format)
        article.tags = tags
        article.is_public = True
        article.previous_versions = [text_content.key()]
        article.published_on = published_on
        article.updated_on = published_on
        # TODO:
        # article.excerpt
        # article.html_body
        article.put()
        logging.info("imported article, url: '%s'" % permalink)

def main():
    mappings = [
        ('/', IndexHandler),
        ('/index.html', IndexHandler),
        ('/atom.xml', AtomHandler),
        ('/archives.html', ArchivesHandler),
        ('/article/(.*)', ArticleHandler),
        ('/tag/(.*)', TagHandler),
        ('/software/', AddIndexHandler),
        ('/software/(.+)/', AddIndexHandler),
        ('/forum_sumatra/rss.php', ForumRssRedirect),
        ('/forum_sumatra/(.*)', ForumRedirect),
        ('/app/edit', EditHandler),
        ('/app/delete', DeleteUndeleteHandler),
        ('/app/undelete', DeleteUndeleteHandler),
        ('/app/draftsanddeleted', DraftsAndDeletedHandler),
        # only enable /import before importing and disable right
        # after importing, since it's not protected
        ('/import', ImportHandler),
    ]
    app = webapp.WSGIApplication(mappings,debug=True)
    app = redirect_from_appspot(app)
    app = dectect_localhost(app)
    wsgiref.handlers.CGIHandler().run(app)

if __name__ == "__main__":
  main()
