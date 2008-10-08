#!/usr/bin/env python

import sys, os.path
import web, settings
from settings import db, render

options = r'(?:\.(html|xml|rdf|n3|json))'

urls = (
  r'/app/', 'index',
  r'/app/login', 'login',
  r'/static/foo', 'foo',
  # when deployed, this is taken care of by the web server
  #r'/static/(.*)', 'staticdata',
  #r'/static/css/style.css', 'stylecss',
)

class staticdata:
    def GET(self, path):
        print("staticdata")
        if not web.config.debug:
            raise web.notfound
        print("path: %s" % path)
        assert '..' not in path, 'security'
        path2 = os.path.join("..", "www", "static", path[1:])
        print("path2='%s'" % path2)
        return file(path2).read()

class stylecss:
    def GET(self):
        return "foo"

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
