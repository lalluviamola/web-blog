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
class Index(webapp.RequestHandler):
    def get(self):
        template_out(self.response, "tmpl/index.html")

class AddIndex(webapp.RequestHandler):
    def get(self):
        new_url = self.request.url + "index.html"
        return self.redirect(new_url)

class ForumRedirect(webapp.RequestHandler):
    def get(self, path):
        new_url = "http://forums.fofou.org/sumatrapdf/" + path
        return self.redirect(new_url)
class ForumRssRedirect(webapp.RequestHandler):
    def get(self):
        return self.redirect("http://forums.fofou.org/sumatrapdf/rss")

def main():
    mappings = [  ('/', Index),
        ('/software/', AddIndex),
        ('/software/fofou/', AddIndex),
        ('/software/sumatrapdf/', AddIndex),
        ('/software/wtail/', AddIndex),
        ('/software/scdiff/', AddIndex),
        ('/forum_sumatra/rss.php', ForumRssRedirect),
        ('/forum_sumatra/(.*)', ForumRedirect),
    ]
    application = webapp.WSGIApplication(mappings,debug=True)
    application = redirect_from_appspot(application)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == "__main__":
  main()
