# This code is in Public Domain. Take all the code you want, we'll just write more.
import pickle, bz2, os.path, string, datetime, sys, codecs

PICKLED_DATA = os.path.join("..", "..", "..", "wp_posts.dat.bz2")
FILES_DIR = os.path.join("..", "srcblog")

(p_id, p_author, p_date, p_date_gmt, p_content, p_title, p_cat, p_exc, p_lat, p_lon, p_status, p_comment_status, p_ping_status, p_password, p_name, p_to_ping, p_pinged, p_modified, p_modified_gmt, p_content_filtered, p_parent, p_guid, p_menu_order, p_type, p_mime_type, p_comment_count) = range(26)

(cat_id, cat_name, cat_nicename) = range(3)

def to_datetime(val):
  #print("type of '%s' is '%s'" % (str(val), type(val)))
  dt = datetime.datetime.utcfromtimestamp(val)
  #print("'%s' is '%s'" % (str(val), dt.isoformat()))
  return dt

def to_unicode(val):
  #if isinstance(val, unicode): return val
  return unicode(val, 'latin-1')

def dir_exists(path): return os.path.exists(path) and os.path.isdir(path)

def make_dir(path):
  if not dir_exists(path): os.makedirs(path)

def write_to_file(filename, txt_uni):
  make_dir(os.path.dirname(filename))
  fo = codecs.open(filename, encoding='utf-8', mode="w")
  fo.write(txt_uni)
  fo.close()

def get_cat(cats, catid):
  for c in cats:
    if c[cat_id] == catid:
      return c[cat_name]
  return None

def main():
  if not os.path.exists(PICKLED_DATA):
    print("File %s doesn't exists" % PICKLED_DATA)
    return
  print("Reading '%s'" % PICKLED_DATA)
  fo = bz2.BZ2File(PICKLED_DATA, "r")
  data = pickle.load(fo)
  fo.close()
  print("Finished reading")
  posts = data["posts"]
  cats = data["categories"]
  dates_txt = {}
  total = len(posts)
  n = 1
  for p in posts:
    date = p[p_date_gmt]
    body_latin1 = p[p_content]
    body = to_unicode(body_latin1)
    title_latin1 = p[p_title]
    cat = p[p_cat]
    if cat:
      #print("Looking for cat: %d" % cat)
      cat = get_cat(cats, cat)
    if title_latin1:
      title = to_unicode(title_latin1)
    if not date:
      date = p[p_date]
    if not date:
      filename = "draft_%d.txt" % n
      filepath = os.path.join(FILES_DIR, filename)
      print("Writing (%d out of %d) %s" % (n, total, filepath))
      write_to_file(filepath, txt)
      n += 1
      continue
    date_txt = date.strftime("%Y-%m-%d")
    if date_txt in dates_txt:
      count = dates_txt[date_txt]
      dates_txt[date_txt] = count + 1
      filename = "%s_%d.txt" % (date_txt, count)
    else:
      dates_txt[date_txt] = 1
      filename = date_txt + ".txt"
    (year, month) = date_txt.split("-")[:2]
    fulldate = str(date)
    txt = u"Date: %s\n" % str(date)
    txt += u"Format: wphtml\n"
    #if cat: txt += u"Category: %s\n" % to_unicode(cat)
    if title:
      txt += u"Title: %s\n" % title
    if p[p_type]:
      txt += u"Type: %s\n" % to_unicode(p[p_type])
    if p[p_mime_type]:
      txt += u"MimeType: %s\n" % to_unicode(p[p_mime_type])
    txt += "\n" + body
    filepath = os.path.join(FILES_DIR, year, month, filename)
    print("Writing (%d out of %d) %s" % (n, total, filepath))
    write_to_file(filepath, txt)
    n += 1
  print("%d posts" % len(posts))

if __name__ == "__main__":
  main()

