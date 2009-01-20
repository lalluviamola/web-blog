# Author: Krzysztof Kowalczyk
# Dates: 2005-12-28 started
# This script reads the file given as first argument (knowledge-base.txt if
# not given) and generates a set of static html pages.

import sys, string, os, os.path, urllib, re, time, tempfile, md5
import markdown2
from pygments import highlight
from pygments.lexers import *
from pygments.formatters import HtmlFormatter

# directory where we'll generate the files
OUTDIR = "."

KNOWN_LANGUAGES = ["c", "c++", "cpp", "c#", "python", "java", "diff", "diffu", "html", "javascript", "makefile", "perl", "lisp", "elisp", "scheme", "sh", "sql", "tcl", "php", "batch", "xml", "lua"]

def known_lang(lang):
    return lang in KNOWN_LANGUAGES

lang_to_lex = {
    "python" : PythonLexer,
    "c" : CLexer,
    "c++" : CppLexer,
    "cpp" : CppLexer,
    "java" : JavaLexer,
}

def lexer_from_lang(lang):
    if lang == "python": return PythonLexer()
    if lang == "c": return CLexer()
    if lang in ["c++", "cpp"]: return CppLexer()
    if lang == "java": return JavaLexer()
    if lang == "c#": return CSharpLexer()
    if lang == "sh": return BashLexer()
    if lang == "batch": return BatchLexer()
    if lang == "sql": return SqlLexer()
    if lang in ["diff", "diffu"]: return DiffLexer()
    if lang == "makefile": return MakefileLexer()
    if lang == "html": return HtmlLexer()
    if lang == "javascript": return JavascriptLexer()
    if lang == "php": return PhpLexer()
    if lang == "xml": return XmlLexer()
    if lang in ["elisp", "lisp", "scheme"]: return SchemeLexer()
    if lang == "lua": return LuaLexer()
    if lang == "perl": return PerlLexer()
    return None

# convert 'content' text to html using enscript
def code_to_html(code, lang):
    lexer = lexer_from_lang(lang)
    if lexer:
        odata = highlight(code, PythonLexer(), HtmlFormatter())
    else:
        odata = "<pre>\n" + encode_code(code) + "</pre>"

    # Strip header and footer
#    beg = odata.find('<PRE>')
#    if beg < 0: beg = 0
#    end = odata.rfind('</PRE>')
#    if end < 0:
#        end = len(odata)
#    else:
#        end = end + 6
#    odata = odata[beg:end]
    return odata

TAGS_TXT = "Tags".lower()
TITLE_TXT = "Title".lower()
DATE_TXT = "Date".lower()

# valid attributes of a post, normalized to lower case
valid_attrs = [TITLE_TXT, DATE_TXT, TAGS_TXT]

# if article has a "hidden" tag, then we shouldn't show it. Those are like drafts
HIDDEN_TXT = "hidden".lower()

def markup2(txt):
    #txt = txt.decode('ascii').encode('utf-8')
    try:
        res = markdown2.markdown(txt)
    except:
        print(txt)
        raise
    #res = res.decode('utf-8').encode('iso-8859-1')
    return res

def empty_str(str):
    return 0 == len(str.strip())

# create a sane file name out of arbitray text
def sanitize_for_filename(txt):
     # characters invalid in a filename are replaced with "-"
    to_replace = [" ", "/", "\\", "\"", "'", "(", ")"]
    for c in to_replace:
        txt = txt.replace(c, "-")
    return txt.lower()

# covert arbitrary string to a valid, sanitized url
def txt_to_url(txt):
    return urllib.quote_plus(sanitize_for_filename(txt))

def valid_attr(attr):
    return attr.lower() in valid_attrs

# article 'Date' tag must be in YYYY-MM-DD format so that they can be sorted as strings
_valid_article_date_rx = re.compile("^\d\d\d\d-\d\d-\d\d$")

def valid_article_dates(article_dates):
    if 0 == len(article_dates):
        return False
    for article_date in article_dates:
        re_match = _valid_article_date_rx.search(article_date)
        if None == re_match:
            return False
    return True

# given a string in the format of "@[\*]+$attr:[\w]*$value", return (attr, value)
def get_attr_value(str):
    assert str.startswith("@")
    (attr, value) = str.split(":", 1)
    return (attr[1:].strip(), value.strip())

def is_attr_tags(str): return str == TAGS_TXT

class Article(object):
    MARKUP = 1
    CODE = 2
    def __init__(self):
        self.attrs = {}
        # we support code embedded inside text. We need to do some pre-processing
        # on code (e.g. in order to implement syntax highlighting) so when we
        # parse the document, we construct a list of body parts, each part
        # is either Article.MARKUP or ARTICLE.CODE. 
        self.body_parts = [] # list of (txt, list_type [, language])
        # we need to keep temporary date during parsing, cur_list is a list of
        # lines of text for a currently parsed body part, cur_type its type and
        # cur_lang is langugage tag for CODE types
        self.cur_list = []
        self.cur_type = None # MARKUP or CODE
        self.cur_lang = None

        # those are build during parsing from attributes of an article
        self.dates = None # list of dates, calculated for 'Date' attribute
        self.tags = None # list of tags, calculated from 'Tags' attribute
        self.title = None # calculated from 'Title' attribute
        self.url = None # calculated from 'Title' attribute
        self.html_file_name = None # calculated from 'Title' attribute

    def _current_body_part(self):
        cur_txt = string.join(self.cur_list, "")
        #if Article.CODE == self.cur_type:
        #    print "*%s*" % cur_txt
        return (cur_txt, self.cur_type, self.cur_lang)

    def get_body_parts(self):
        parts = self.body_parts
        parts.append(self._current_body_part())
        return parts
    
    def _get_body_txt(self):
        return string.join(self.get_body_parts())

    def get_raw_txt(self):
        raw = []
        for parts in self.get_body_parts():
            txt = parts[0]
            raw.append(txt)
        return string.join(raw)

    def add_attr(self, attr, val):
        attr = attr.lower()
        assert not self.attrs.has_key(attr)
        if TAGS_TXT == attr:
            val = val.lower().strip()
            self.tags = [t.lower().strip() for t in val.split(",")]
        elif DATE_TXT == attr:
            val = val.strip()
            self.dates = val.split()
        elif TITLE_TXT == attr:
            val = val.strip()
            self.title = val.strip()
            self.url = txt_to_url(self.title) + ".html"
            self.html_file_name = sanitize_for_filename(self.title) + ".html"            
        else:
            print "unsupported attr '%s'" % attr
            assert False, "unsupported attr"
        self.attrs[attr] = val
    
    def start_markup(self):
        if 0 != len(self.cur_list):
            assert self.cur_type != None
            self.body_parts.append(self._current_body_part())
        self.cur_list = []
        self.cur_type = Article.MARKUP

    def start_code(self, lang = None):
        if 0 != self.cur_list:
            assert self.cur_type != None
            self.body_parts.append(self._current_body_part())
        self.cur_list = []
        self.cur_type = Article.CODE
        self.cur_lang = lang

    def add_to_body(self,l):  self.cur_list.append(l)

    def is_hidden(self):
        if None == self.tags:
            return False
        return HIDDEN_TXT in self.tags

    # for debugging, dump your state
    def dump(self):
        for (attr, val) in self.attrs.items():
            print "'%s': %s" % (attr, val)
        print "'Body': %s" % self._get_body_txt()
        print "is_hidden: %s" % str(self.is_hidden())

    def assert_if_invalid(self):
        if None == self.dates:
            self.dump()
            assert None != self.dates

        if not valid_article_dates(self.dates):
            self.dump()
            assert valid_article_dates(self.dates)

        if None == self.tags:
            self.dump()
            assert None != self.tags
            
        if None == self.title:
            self.dump()
            assert None != self.title

        if None == self.url:
            self.dump()
            assert None != self.url

CODE_START_TXT = "<code"
CODE_END_TXT = "</code>"

# states for parsing state machine
ST_START, ST_PARSING_ATTRS, ST_IN_TEXT, ST_IN_CODE = range(4)

articles = []
state = ST_START
cur_article = None

def process_file(file_name):
    global articles, state, cur_article

    articles = []
    state = ST_START
    cur_article = None

    fo = open(file_name, "rb")

    def parse_lang(l):
        global cur_article
        l = l.strip()
        lang = l[5:-1].strip()
        if empty_str(lang):
            cur_article.cur_lang = None
        else:
            if not known_lang(lang):
                print "Unknown language '%s' in line '%s'" % (lang, l)
                assert False
            cur_article.cur_lang = lang

    def do_first_attribute(l):
        global cur_article, articles, state
        cur_article = Article()
        articles.append(cur_article)
        (attr, value) = get_attr_value(l)
        cur_article.add_attr(attr, value);
        state = ST_PARSING_ATTRS

    for l in fo.readlines():
        #print l.strip()
        if ST_START == state:
            # this is the initial state and lasts until finding beggining of
            # a first article (first attribute). It skips comments and empty lines
            #print " state: ST_START"
            if l.startswith("#"):  # skip comments
                continue
            if empty_str(l): # skip empty lines
                continue
            if l.startswith("@"):
                assert None == cur_article
                do_first_attribute(l)
            else:
                assert False, "unexpected text"
        elif ST_PARSING_ATTRS == state:
            # parsing attributes of a given article
            #print " state: ST_PARSING_ATTRS"
            if l.startswith("@"):
                assert None != cur_article
                (attr, value) = get_attr_value(l)
                cur_article.add_attr(attr, value)
            elif l.startswith(CODE_START_TXT):
                state = ST_IN_CODE
                cur_article.start_code()
                parse_lang(l)
            else:
                state = ST_IN_TEXT
                cur_article.start_markup()
                cur_article.add_to_body(l)
        elif ST_IN_CODE == state:
            # we are parsing block of text enclosed in <code ...> </code> tags
            #print " state: ST_IN_CODE"
            #print "_%s_" % l
            if l.startswith(CODE_END_TXT):
                state = ST_IN_TEXT
                cur_article.start_markup()
            else:
                cur_article.add_to_body(l)
        elif ST_IN_TEXT == state:
            # parsing the text of the article in a markup language
            #print " state: ST_IN_TEXT"
            if l.startswith("@"):
                do_first_attribute(l)
            elif l.startswith(CODE_START_TXT):
                state = ST_IN_CODE
                cur_article.start_code()
                parse_lang(l)
            else:
                cur_article.add_to_body(l)
        else:
            assert False    
    assert state != ST_IN_CODE, "<code ...> tag without enclosing </code>"
    fo.close()
    return articles

def write_to_file(file_name, txt):
    fo = open(file_name, "wb")
    fo.write(txt)
    fo.close()

def get_file(file_name):
    fo = open(file_name)
    txt = fo.read()
    fo.close()
    return txt

_files_cache = {}
def get_file_replace_vars(file_name, title, creation_date):
    if not _files_cache.has_key(file_name):
        fo = open(file_name)
        txt = fo.read()
        fo.close()
        _files_cache[file_name] = txt
    txt = _files_cache[file_name]
    txt = txt.replace("$title", title)
    txt = txt.replace("$creation-date", creation_date)
    return txt

def today_as_yyyy_mm_dd(): return time.strftime("%Y-%m-%d", time.localtime())

def in_tag(tag, txt):return '<%s>%s</%s>' % (tag, txt, tag)

def in_link(url, title): return '<a href="%s">%s</a>' % (url, title)

def in_font_size(txt, size="-1"): 
    return '<font size="%s">%s</font>' % (size, txt)

def in_font_color(txt, color):
    return '<font color="%s">%s</font>' % (color, txt)

def in_gray(txt): return in_font_color(txt, "gray")

def encode_code(text):
    text = text.replace("&","&amp;")
    text = text.replace("<","&lt;")
    text = text.replace(">","&gt;")
    return text

def gen_html(articles):
    global OUTDIR
    hidden_count = 0

    tag_article_map = {} # maps tags to a list of articles
    def build_tag_article_map(article):
        for tag in article.tags:
            if tag_article_map.has_key(tag):
                tag_article_map[tag].append(article)
            else:
                tag_article_map[tag] = [article]

    date_article_map = {}
    def build_date_article_map(article):
        for dt in article.dates:
            if date_article_map.has_key(dt):
                date_article_map[dt].append(article)
            else:
                date_article_map[dt] = [article]

    urls = {} # for finding titles that would end-up in duplicate urls
    all_articles_count = len(articles)
    all_articles = [article for article in articles if not article.is_hidden()]
    filtered_articles_count = len(articles)
    hidden_count = all_articles_count - filtered_articles_count
    for article in all_articles:
        article.assert_if_invalid()
        url = article.url
        # print "__%s__" % url
        if urls.has_key(url):
            assert not urls.has_key(url), "title '%s' creates a duplicate url" % article.title
        urls[url] = True

    for article in all_articles:
        build_tag_article_map(article)
        build_date_article_map(article)

    print "Finished processing"
    print "Number of articles: %d (hidden: %d)" % (len(articles), hidden_count)
    print "Number of tags: %d" % len(tag_article_map)

    links_per_page = 25

    all_articles.sort(lambda x,y: cmp(y.dates[0], x.dates[0]))
    all_articles_count = len(all_articles)
    pages_count = (all_articles_count +  links_per_page - 1) / links_per_page

    html_footer_txt = get_file("footer.html.txt")

    def gen_tags(txt, tags, tag_to_unlink=None):
        txt = ['<div class="tags">', txt]
        for tag in tags:
            count_txt = in_gray(" (%s) " % len(tag_article_map[tag]))
            if tag == tag_to_unlink:
                txt.append(" " + tag + count_txt)
            else:
                url = txt_to_url("tag-%s" % sanitize_for_filename(tag)) + ".html"
                link_txt = in_link(url, tag) + count_txt
                txt.append(link_txt)
        txt.append("</div>")
        return string.join(txt, "\n")

    print "pages_count = %d" % pages_count
    # generate html index pages index.html for the first page and index-$n.html
    # for all subsequent pages. Those pages have all tags at the top followed
    # by a list of $linkes_per_page links to articles, sorted by date, with
    # the most recent at the top

    all_tags_sorted = tag_article_map.keys()
    all_tags_sorted.sort()

    for page_no in range(pages_count):
        title = "Index of all articles"
        creation_date = today_as_yyyy_mm_dd()
        html_header_txt = get_file_replace_vars("header.html.txt", title=title, creation_date=creation_date)
        html = [html_header_txt]

        tags_txt = gen_tags("Tags: ", all_tags_sorted)
        html.append(tags_txt)
    
        html.append('<div id="kb">')
        first_article_no = page_no * links_per_page + 1
        last_article_no = (page_no + 1) * links_per_page
        if last_article_no > all_articles_count:
            last_article_no = all_articles_count

        html.append("<p>Recent articles (%d - %d):</p>" % (first_article_no, last_article_no))

        html.append("<ul>")
        articles_on_page = all_articles[first_article_no-1 : last_article_no]
        for article in articles_on_page:
            date_txt = in_font_size(in_gray("(%s)" % article.dates[0]))
            link_txt = in_link(article.url, article.title)
            html.append("<li>%s %s</li>" % (link_txt, date_txt))
        html.append("</ul>")
        
        if pages_count > 1:
            html.append("<p/><center>")
            txt = "previous"
            if page_no > 0:
                page_name = "index.html"
                if page_no > 1:
                    page_name = "index-%d.html" % (page_no-1)
                txt = in_link(page_name, txt)
            html.append(txt)

            html.append(" &deg; ")

            txt = "next"
            if page_no != pages_count -1:
                txt = in_link("index-%d.html" % (page_no + 1), txt)
            html.append(txt)
            html.append("</center>")

        html.append('</div>')
        html.append(tags_txt)
        html.append("<p> </p>")
        html.append(html_footer_txt)

        html_txt = string.join(html, "\n")
        file_name = "index-%d.html" % page_no
        if 0 == page_no:
            file_name = "index.html"
        write_to_file(os.path.join(OUTDIR, file_name), html_txt)

    # for each article, generate "$url.html" file
    for article in all_articles:
        title = article.title
        creation_date = article.dates[0]
        html_header_txt = get_file_replace_vars("header.html.txt", title=title, creation_date=creation_date)
        html = [html_header_txt]

        tags = article.tags
        tags.sort()
        tags_txt = gen_tags("Tags: ", tags)
        html.append(tags_txt)
        html.append('<div id="kb">')

        html.append('<p><center><font size="+1"><b>%s</b></font></center></p>' % title)
        for parts in article.get_body_parts():
            txt = parts[0]
            part_type = parts[1]
            lang = parts[2]
            if Article.MARKUP == part_type:
                body_html = markup2(txt)
            else:
                assert Article.CODE == part_type
                body_html = code_to_html(txt, lang)
            html.append(body_html)

        html.append('</div>')
        html.append(tags_txt)
        html.append("<p> </p>")
        html.append(html_footer_txt)
        html_txt = string.join(html, "\n")
        write_to_file(os.path.join(OUTDIR, article.html_file_name), html_txt)

    # for each tag, generate "tag-$tag.html" file
    for tag in tag_article_map.keys():
        title = "Articles tagged with <b>%s</b> tag:" % tag
        creation_date = today_as_yyyy_mm_dd()
        html_header_txt = get_file_replace_vars("header.html.txt", title=title, creation_date=creation_date)
        html = [html_header_txt]

        tags_txt = gen_tags("Tags: ", all_tags_sorted, tag)
        html.append(tags_txt)
        html.append('<div id="kb">')

        articles_with_tag = tag_article_map[tag]
        articles_with_tag.sort(lambda x,y: cmp(y.dates[0], x.dates[0]))

        # TODO: should probably break up into page is a number of articles is large
        # (same limit as for index page)
        html.append("<p>%s</p>" % title)
        html.append("<ul>")
        for article in articles_with_tag:
            date_txt = in_font_size(in_gray("(%s)" % article.dates[0]))
            link_txt = in_link(article.url, article.title)
            html.append("<li>%s %s</li>" % (link_txt, date_txt))
        html.append("</ul>")

        html.append('</div>')
        html.append(tags_txt)
        html.append("<p> </p>")
        html.append(html_footer_txt)
        html_txt = string.join(html, "\n")
        file_name = "tag-%s.html" % sanitize_for_filename(tag)
        write_to_file(os.path.join(OUTDIR, file_name), html_txt)

def usage_and_exit():
    print "Usage: genkbhtml.py [dir] [file-to-process]"
    sys.exit(0)

def main():
    global OUTDIR
    if len(sys.argv) != 3:
        usage_and_exit()
    OUTDIR = sys.argv[1]
    try:
        os.mkdir(OUTDIR)
    except OSError:
        # directory already exists
        pass

    file_to_process = sys.argv[2]
    articles = process_file(file_to_process)
    gen_html(articles)

if __name__ == "__main__":
    main()
