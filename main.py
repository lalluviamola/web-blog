# This code is in Public Domain. Take all the code you want, we'll just write more.
import os
import string
import time
import datetime
import StringIO
import pickle
import textile
import wsgiref.handlers
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from django.utils import feedgenerator
from django.template import Context, Template
import logging

# HTTP codes
HTTP_NOT_ACCEPTABLE = 406
HTTP_NOT_FOUND = 404

TYPE_ARTICLE = "article"
TYPE_BLOG = "blog entry"
ALL_TYPES = [TYPE_ARTICLE, TYPE_BLOG]

(FORMAT_TEXT, FORMAT_HTML, FORMAT_TEXTILE, FORMAT_MARKDOWN) = ("text", "html", "textile", "markdown")
ALL_FORMATS = [FORMAT_TEXT, FORMAT_HTML, FORMAT_TEXTILE, FORMAT_MARKDOWN]

class TextContent(db.Model):
    content = db.TextProperty(required=True)
    published = db.DateTimeProperty(auto_now_add=True)
    format = db.StringProperty(required=True,choices=set(ALL_FORMATS))

class Article(db.Model):
    permalink = db.StringProperty(required=True)
    public = db.BooleanProperty(default=False)
    title = db.StringProperty()
    article_type = db.StringProperty(required=True, choices=set(ALL_TYPES))
    # copy of TextContent.content
    body = db.TextProperty(required=True)
    excerpt = db.TextProperty()
    html_body = db.TextProperty()
    # copy of TextContent.published of first version
    published = db.DateTimeProperty(auto_now_add=True)
    # copy of TextContent.published of last version
    updated = db.DateTimeProperty(auto_now_add=True)
    # copy of TextContent.format
    format = db.StringProperty(required=True,choices=set(ALL_FORMATS))
    #assoc_dict = db.BlobProperty()
    tags = db.StringListProperty(default=[])
    tag_keys = db.ListProperty(db.Key, default=[])
    embedded_code = db.StringListProperty()
    # points to TextContent
    previous_versions = db.ListProperty(db.Key, default=[])

    def rfc3339_published(self):
        return self.published.strftime('%Y-%m-%dT%H:%M:%SZ')

    def rfc3339_updated(self):
        return self.updated.strftime('%Y-%m-%dT%H:%M:%SZ')

def redirect_from_appspot(wsgi_app):
    def redirect_if_needed(env, start_response):
        if env["HTTP_HOST"].startswith('kjkblog.appspot.com'):
            import webob, urlparse
            request = webob.Request(env)
            scheme, netloc, path, query, fragment = urlparse.urlsplit(request.url)
            url = urlparse.urlunsplit([scheme, 'blog.kowalczyk.info', path, query, fragment])
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

def article_gen_html_body(article):
    if article.html_body: return
    if article.format == "textile":
        txt = article.body.encode('utf-8')
        body = textile.textile(txt, encoding='utf-8', output='utf-8')
        body =  unicode(body, 'utf-8')
        article.html_body = body
    elif article.format == "text":
        # TODO: probably should just send as plain/text and a
        # separate template
        article.html_body = article.body
    elif article.format == "html":
        article.html_body = article.body
    
# responds to /
class BlogIndexHandler(webapp.RequestHandler):
    def get(self):
        is_admin = users.is_current_user_admin()
        if is_admin:
            article = db.GqlQuery("SELECT * FROM Article ORDER BY published DESC").get()
        else:
            article = db.GqlQuery("SELECT * FROM Article WHERE public = True ORDER BY published DESC").get()
        article_gen_html_body(article)
        if is_admin:
            login_out_url = users.create_logout_url("/")
        else:
            login_out_url = users.create_login_url("/")
        vals = { 
            'is_admin' : is_admin,
            'login_out_url' : login_out_url,
            'article' : article,
            'show_analytics' : False,
        }
        template_out(self.response, "tmpl/index.html", vals)

class EditHandler(webapp.RequestHandler):
    def get(self):
        # TODO: use local copy if in local testing, google's
        # if deployed
        jquery_url = "/static/js/jquery.js"
        #jquery_url = "http://ajax.googleapis.com/ajax/libs/jquery/1.2.6/jquery.js"
        article = None
        article_id = self.request.get('article_id')
        if article_id:
            article = db.get(db.Key.from_path('Article', int(article_id)))
        vals = {
            'jquery_url' : jquery_url,
            'article' : article,
        }
        template_out(self.response, "tmpl/edit.html", vals)

# responds to /blog/*
class BlogHandler(webapp.RequestHandler):
    def get(self,url):
        permalink = "blog/" + url
        is_admin = users.is_current_user_admin()
        if is_admin:
            article = Article.gql("WHERE permalink = :1", permalink).get()
        else:
            article = Article.gql("WHERE permalink = :1 AND public = :2", permalink, True).get()
        if not article:
            vals = { "url" : permalink }
            template_out(self.response, "tmpl/blogpost_notfound.html", vals)
            return
        article_gen_html_body(article)
        vals = { "article" : article }
        template_out(self.response, "tmpl/blogpost.html", vals)

def article_for_archive(article):
    new_article = {}
    new_article["permalink"] = article.permalink
    new_article["title"] = article.title
    new_article["published"] = article.published
    new_article["day"] = article.published.day
    return new_article

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

# responds to /blog/archive.html
class BlogArchiveHandler(webapp.RequestHandler):
    def get(self):
        # TODO: memcache this if turns out to be done frequently
        is_admin = users.is_current_user_admin()
        if is_admin:
            articlesq = db.GqlQuery("SELECT * FROM Article ORDER BY published DESC")
        else:
            articlesq = db.GqlQuery("SELECT * FROM Article WHERE public = True ORDER BY published DESC")
        curr_year = None
        curr_month = None
        years = []
        for a in articlesq:
            date = a.published
            y = date.year
            m = date.month
            a.day = date.day
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
            'is_admin' : is_admin,
        }
        template_out(self.response, "tmpl/archive.html", vals)

class AtomHandler(webapp.RequestHandler):
    def get(self):
        # TODO: memcache this if turns out to be done frequently
        feed = feedgenerator.Atom1Feed(
            title = "Krzysztof Kowalczyk blog",
            link = "http://blog.kowalczyk.info/feed/",
            description = "Krzysztof Kowalczyk blog")

        articlesq = db.GqlQuery("SELECT * FROM Article WHERE public = True ORDER BY published DESC")
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
            pubdate = a.published
            feed.add_item(title=title, link=link, description=description, pubdate=pubdate)
        feedtxt = feed.writeString('utf-8')
        self.response.headers['Content-Type'] = 'text/xml'
        self.response.out.write(feedtxt)
    
class AddIndexHandler(webapp.RequestHandler):
    def get(self, sub=None):
        new_url = self.request.url + "index.html"
        return self.redirect(new_url)

class ForumRedirect(webapp.RequestHandler):
    def get(self, path):
        new_url = "http://forums.fofou.org/sumatrapdf/" + path
        return self.redirect(new_url)

class ForumRssRedirect(webapp.RequestHandler):
    def get(self):
        return self.redirect("http://forums.fofou.org/sumatrapdf/rss")

(POST_URL, POST_DATE, POST_FORMAT, POST_BODY, POST_TITLE) = ("url", "date", "format", "body", "title")

def uni_to_utf8(val): return unicode(val, "utf-8")
 
# import one or more posts from old text format
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
        permalink = post[POST_URL]
        permalink = uni_to_utf8(permalink)
        article = Article.gql("WHERE permalink = :1", permalink).get()
        if article:
            logging.info("post with url '%s' already exists" % permalink)
            return self.error(HTTP_NOT_ACCEPTABLE)
        published = post[POST_DATE]
        format = post[POST_FORMAT]
        format = uni_to_utf8(format)
        assert format in ALL_FORMATS
        body = post[POST_BODY] # body comes as utf8
        body = uni_to_utf8(body)
        textContent = TextContent(content=body, published=published, format=format)
        textContent.put()
        title = post[POST_TITLE]
        title = uni_to_utf8(title)
        article = Article(permalink=permalink, title=title, body=body, format=format, article_type=TYPE_BLOG)
        article.public = True
        article.previous_versions = [textContent.key()]
        article.published = published
        article.updated = published
        # TODO:
        # article.excerpt
        # article.html_body
        article.put()
        logging.info("imported post with url '%s'" % permalink)

def main():
    mappings = [
        ('/', BlogIndexHandler),
        ('/index.html', BlogIndexHandler),
        ('/atom.xml', AtomHandler),
        ('/archives.html', BlogArchiveHandler),
        ('/blog/(.*)', BlogHandler),
        ('/software/', AddIndexHandler),
        ('/software/(.+)/', AddIndexHandler),
        ('/forum_sumatra/rss.php', ForumRssRedirect),
        ('/forum_sumatra/(.*)', ForumRedirect),
        ('/app/edit', EditHandler),
        # only enable /import before importing and disable right
        # after importing, since it's not protected
        ('/import', ImportHandler),
    ]
    application = webapp.WSGIApplication(mappings,debug=True)
    #application = redirect_from_appspot(application)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
