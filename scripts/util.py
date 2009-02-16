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

def onlyascii(c):
  if c in " _.;,-":
    return c
  if ord(c) < 48 or ord(c) > 127:
    return ''
  else: 
    return c

def urlify(s):
  s = s.strip().lower()
  s = filter(onlyascii, s)
  for c in [" ", "_", "=", ".", ";", ":", "/", "\\", "\"", "'", "(", ")", "{", "}", "?", ","]:
    s = s.replace(c, "-")
  # TODO: a crude way to convert two-or-more consequtive '-' into just one
  # it's really a job for regex
  while True:
    new = s.replace("--", "-")
    if new == s:
      break
    #print "new='%s', prev='%s'" % (new, s)
    s = new
  s = s.strip("-")[:48]
  s = s.strip("-")
  return s
