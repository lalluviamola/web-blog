#!/usr/bin/env python

import sys
import web
web.config.debug = True
import settings
from settings import db, render

options = r'(?:\.(html|xml|rdf|n3|json))'

urls = (
  '/', 'index',
  '/app/', 'index',
  '/app/hello', 'hello'
)

class index:
    def GET(self):
        return render.index()

class hello:
    def GET(self):
        return "<html><body>hello</body></html>"

app = web.application(urls, globals(), autoreload=True)
#settings.setup_session(app)

if "-test" not in sys.argv:
    web.wsgi.runwsgi = lambda func, addr=None: web.wsgi.runfcgi(func, addr)
else:
    print("Using embedded web server")
    del sys.argv[sys.argv.index("-test")]

if __name__ == "__main__":
    app.run()
