#!/usr/bin/env python
import cgi
import re
import jsrefgentmpl

g_source = """
!number Number 2 1.5 2.5e3 0xFF 010
ass(_2_+2 == 4); // numbers are 64-bit floating point
ass(_1.5_ == 3/2); // no separate integer type
ass(_2.5e3_ == 2500; // 2.5 * 10^3 exponential notation
ass(_0xFF_ == 255); // hexadecimal
ass(_010_ == 8); // octal
---
ass(   2 _+_ 2 == 4); // addition
ass(  10 _-_ 3 == 7); // subtraction
ass(   3 _*_ 8 == 24); // multiplication
ass( 123 _/_ 10 == 12.3); // real (not integer) division
ass(1234 _%_ 100 == 34); // modulo (reminder)
---
var n=3;  n _+=_ 30; ass(n == 33); // compute & store
var n=33; n _-=_ 30; ass(n == 3); // x *= is the same

!string String 'abc' "abc" "line\u000D\u000A"
var s=="str"; // double or single quotes
var s=='str';
ass("str" _+_ "ing" == "string"); // + concatenates

!boolean Boolean  true false
var t=_true_; ass(t);
var f=_false_; ass(!f); // ! is boolean not
ass((true _&&_ false) == false); // && is boolean and
ass((true _||_ false) == true); // || is boolean or
ass((true _?_ 'a' _:_ 'b') == 'a'); // compact if-else
ass((false _?_ 'a' _:_ 'b') == 'b');

!date Date Date() new Date(1999,12-1,31,23,59)
var now=_new Date()_; // current date
var past=_new Date(_2002,5-1,20,23,59,59,999_)_;
// (year,month-1,day,hr,minutes,seconds,milliseconds)
---
ass(now._getTime()_ > past.getTime());
// Compare dates only by their getTime() or valueOf()
ass(past.getTime() == 1021953599999);
ass(past.getTime() == past._valueOf_());
// Compute elapsed milliseconds by substracting getTime()'s
var hours=(now.getTime()-past.getTime())/3600000;
---
// Example date and time formats:
ass(past._toString_() == 'Mon May 20 23:59:59 EDT 2002');
ass(past._toGMTString_() == 'Tue, 21 May 002 03:59:59 UTC');
ass(past._toUTCString_() = 'Tue, 21 May 2002 03:59:59 UTC');

"""

def tr(s):
	return " <tr>%s </tr>\n" % s

def td(s, cls=None):
	if cls is not None:
		return """%s  <td class="%s">%s   %s%s  </td>%s""" % ("\n", cls, "\n", s, "\n", "\n")
	else:
		return """%s  <td>%s   %s%s  </td>%s""" % ("\n", "\n", s, "\n", "\n")

def span(s, cls=None):
	if cls:
		return """<span class="%s">%s</span>""" % (cls, s)
	return """<span>%s</span>""" % s

class header_row(object):
	def __init__(self, left, right):
		self.left = left
		self.right = right
	def tohtml(self):
		s = span(self.left, "big") + " " + self.right
		#"""<span class="big">%s</span> %s""" % (self.left, self.right)
		return tr(td(s, "header line"))

re_em = re.compile("_(.*?)_")
re_comment = re.compile("(//.*)$")

class row(object):
	def __init__(self, s):
		self.s = s
		self.sepline = False
	def tohtml(self):
		s = self.s.replace("ass(", "assert(");
		s = cgi.escape(s)
		s = re_comment.sub(span(r"\1", "comment"), s)
		s = re_em.sub(span(r"\1", "em"), s)
		cls = None
		if self.sepline: cls = "line"
		return tr(td(s, cls))

class table(object):
	def __init__(self, id):
		self.id = id
		self.rows = []
	def addrow(self, row):
		self.rows.append(row)
	def tohtml(self):
		s = '<table id="%s">\n' % self.id
		for row in self.rows:
			s += row.tohtml()
		s += "</table>"
		return s
	def marklastrowsep(self):
		self.rows[-1].sepline = True

def genhtml(src):
	tables = []
	tbl = None
	for s in src.split("\n"):
		s = s.strip()
		if len(s) == 0: continue
		if s[0] == '!':
			if tbl is not None: tables.append(tbl)
			s = s[1:]
			try:
				(id, left, right) = s.split(" ", 2)
			except:
				print(s)
				raise
			tbl = table(id)
			tbl.addrow(header_row(left, right))
			continue
		if s == "---":
			tbl.marklastrowsep()
			continue
		tbl.addrow(row(s))
	if tbl is not None: tables.append(tbl)
	s = ""
	for tbl in tables:
		s += tbl.tohtml()
		s += "\n<br>\n"
	return s

if __name__ == "__main__":
	html = genhtml(g_source)
	fo = open("jsref.html", "w")
	s = jsrefgentmpl.tmpl.replace("%s", html)
	fo.write(s)
	fo.close()
