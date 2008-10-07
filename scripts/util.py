import os.path, codecs

def dir_exists(path): return os.path.exists(path) and os.path.isdir(path)

def make_dir(path):
    if not dir_exists(path): os.makedirs(path)

def file_read_utf8(filename):
  fo = codecs.open(filename, encoding='utf-8', mode="r")
  txt = fo.read()
  fo.close()
  return txt

def file_write_utf8(filename, txt):
  make_dir(os.path.dirname(filename))
  fo = codecs.open(filename, encoding='utf-8', mode="w")
  fo.write(txt)
  fo.close()

def file_write(filename, txt):
  make_dir(os.path.dirname(filename))
  fo = open(filename, mode="wb")
  fo.write(txt)
  fo.close()
