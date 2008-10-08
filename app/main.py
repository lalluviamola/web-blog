#!/usr/bin/env python
import sys, os.path
import web, settings
from settings import db, render

"""
TODO:
 * slurp files into a database
 * figure out auth scheme to recognize me as logged in
   without the need to serve different files (some JS
   that can tell that a cookie is for a logged in user
   but doesn't allow spoofing the cookie. anyway, that's
   not very important because all it will do is show
   few urls that will direct to pages that are better
   protected anyway)
 * /login, /logout + pwd based auth (pwd can be in a file locally)
 * /app/regenerateall which generates all the static files
   from the database
 * /app/newblog form to post a new blog entry, linked from
   main page if is logged in
"""

urls = (
  r'/app/', 'index',
  r'/app/login', 'login',
  # when deployed, those are taken care of by the web server
  r'/css/(.*)', 'cssdata',
  r'/js/(.*)', 'jsdata',
)

class cssdata:
    def GET(self, path):
        #print("cssdata path: %s" % path)
        if not web.config.debug:
            raise web.notfound
        assert '..' not in path, 'security'
        path = os.path.join("..", "www", "css", path)
        #print("path2='%s'" % path)
        return file(path).read()

class jsdata:
    def GET(self, path):
        #print("jsdata path: %s" % path)
        if not web.config.debug:
            raise web.notfound
        assert '..' not in path, 'security'
        path = os.path.join("..", "www", "js", path)
        #print("path2='%s'" % path2)
        return file(path).read()

class index:
    def GET(self):
        return render.index()

class login:
    def GET(self):
        return "<html><body>login page</body></html>"

class foo:
    def GET(self):
        return "<html><body>foo</body></html>"

app = web.application(urls, globals(), autoreload=True)
#settings.setup_session(app)

if "-test" in sys.argv:
    print("Using embedded web server")
    del sys.argv[sys.argv.index("-test")]
    web.config.debug = True
else:
    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)

if __name__ == "__main__":
    app.run()
