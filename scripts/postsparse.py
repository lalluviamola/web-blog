import os.path, codecs

def parse_blog_post_headers(post_path):
  vals = {}
  fo = codecs.open(post_path, encoding='utf-8', mode="r")
  for l in fo:
    l = l.strip()
    if not l:
      break
    if ": " not in l:
      print("Invalid line:\n'%s'\n" % l)
    (name, val) = l.split(": ", 1)
    name = name.lower()
    vals[name] = val
  fo.close()
  if "date" not in vals:
    print("Invalid post '%s'" % post_path)
    print vals
  assert "date" in vals
  assert "format" in vals
  assert "title" in vals
  vals["title"] = vals["title"].rstrip(".")
  return vals

def get_blog_post_content(post_path):
  fo = codecs.open(post_path, encoding='utf-8', mode="r")
  # skip headers
  for l in fo:
    l = l.strip()
    if not l:
      break
  # the rest is post body  
  lines = [l for l in fo]
  fo.close()
  return "".join(lines)

def is_draft(vals):
  if not "draft" in vals:
    return False
  v = vals["draft"].strip().lower()
  return v in ["1", "yes", "true"]

def skip_file(fname):
  return fname in ["evernote-utf8.txt", "knowledge-base.txt"]

def scan_posts(path):
  def callback(allfiles, dirname, fnames):
    if ".svn" in dirname: return
    if ".git" in dirname: return
    for fname in fnames:
      if skip_file(fname):
        continue
      if fname.endswith(".txt"):
        #print("dir: %s, file: %s" % (dirname, fname))
        filepath = os.path.join(dirname, fname)
        vals = parse_blog_post_headers(filepath)
        if not is_draft(vals):
          vals["file"] = filepath
          allfiles[filepath] = vals
        #print vals

  allfiles = {}
  os.path.walk(path, callback, allfiles)
  return allfiles

