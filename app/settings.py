import os
import tempfile
import web
 
render = web.template.render('templates/')
db = web.database(dbn=os.environ.get('DATABASE_ENGINE', 'sqlite'),
                  db=os.environ.get('MYKB_TABLE', 'mykb_dev'))

#@@@@ is temp directory really okay for sessions??                  
sess_store = tempfile.mkdtemp()             
session = web.session.Session(None, web.session.DiskStore(sess_store))                  
 
def setup_session(app):
    app.add_processor(session._processor)
