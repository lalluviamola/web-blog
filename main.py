# This code is in Public Domain. Take all the code you want, we'll just write more.
import os, string, Cookie, sha, time, random, cgi, urllib, datetime, StringIO, pickle
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

# responds to /
class BlogIndexHandler(webapp.RequestHandler):
    def get(self):
        is_admin = users.is_current_user_admin()
        articlesq = db.GqlQuery("SELECT * FROM Article ORDER BY published DESC")
        for article in articlesq:
            if is_admin or article.public:
                break
        # note: it would show non public article if all of them were private,
        # but that's not the case so we don't care
        vals = { "article" : article }
        template_out(self.response, "tmpl/index.html", vals)

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
        vals = { "article" : article }
        template_out(self.response, "tmpl/blogpost.html", vals)

def article_for_archive(article):
    new_article = {}
    new_article["permalink"] = article.permalink
    new_article["title"] = article.title
    return new_article

# responds to /blog/archive.html
class BlogArchiveHandler(webapp.RequestHandler):
    def get(self):
        # TODO: memcache this if turns out to be done frequently
        articlesq = db.GqlQuery("SELECT * FROM Article ORDER BY published DESC")
        articles = [article_for_archive(a) for a in articlesq]
        vals = { "articles" : articles }
        template_out(self.response, "tmpl/archive.html", vals)

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
        ('/archives.html', BlogArchiveHandler),
        ('/blog/(.*)', BlogHandler),
        ('/software/', AddIndexHandler),
        ('/software/(.+)/', AddIndexHandler),
        ('/forum_sumatra/rss.php', ForumRssRedirect),
        ('/forum_sumatra/(.*)', ForumRedirect),
        # only enable /import before importing and disable right
        # after importing, since it's not protected
        ('/import', ImportHandler),
    ]
    application = webapp.WSGIApplication(mappings,debug=True)
    #application = redirect_from_appspot(application)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
