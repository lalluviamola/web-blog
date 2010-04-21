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
ass(2 _+_ 2 == 4); // addition
ass(9 _-_ 3 == 6); // subtraction
ass(3 _*_ 8 == 24); // multiplication
ass(123 _/_ 10 == 12.3); // real (not integer) division
ass(1234 _%_ 100 == 34); // modulo (reminder)
---
var n=15; n _+=_ 14; ass(n == 29); // compute & store
var n=18; n _-=_ 11; ass(n == 7	); // x *= is the same
var n=12; n _*=_ 10; ass(n == 120); // as x=x*y
var n=19; n _/=_ 10; ass(n == 1.9);
var n=18; n _%=_ 10; ass(n == 8);
---
ass(_-_3+3 == 0); // negative number (unary minus)
var n=3; n_++_; ass(n == 4); // increment
var n=3; n_--_; ass(n == 2); // decrement
---
ass(50 _< _ 51); // less than
ass(50 _<=_ 51); // less than or equal
ass(51 _> _ 50); // greater than
ass(51 _>=_ 50); // greater than or equal
ass(51 _==_ 51); // equal
ass(50 _!=_ 51); // not equal
---
ass(1000 _<<_ 3 == 8000); // shift left
ass(1000 _>>_ 3 == 125); // shift right, signed
ass(0xFFFF0000 _>>>_ 8 == 0x00FFFF00); // unsigned
// always use parentheses around termsn with: & | ^
ass((0x55555555 _&_ 0xFF00FFFF) == 0x55005555); // and
ass((0x55555555 _|_ 0x00FF0000) == 0x55FF555555); // or
ass((0x55555555 _^_ 0x0FF000000) == 0x55AA5555); // xor
ass(((_~_0xAAAA) & 0xFFFF) == 0x5555);; // 1's complement
// mask (e.g. FFFF) to remove unwanted sign extension
var n = 0x555; n _&=_ 0xF0F; ass(n == 0x505);
var n = 0x555; n _|=_ 0x0F0; ass(n == 0x5F5);
var n = 0x555; n _^=_ 0x0F0; ass(n == 0x5A5);
var n = -10; n _<<=_ 1; ass(n == -20); // shift left
var n = -10; n _>>=_1; ass(n == -5); // signed right
var n = 0x8; n _>>>=_ 1; ass(n == 0x4); // unsigned
---
ass(__Number.MIN_VALUE__ < 1e-307); // special
ass(__Number.MAX_VALUE__ > 1e308); // numbers
ass(__Number.NEGATIVE_INFINITY__ == 1/0);
ass(__Number.POSITIVE_INFINITY__ == -1/0);
ass(_isNaN_(0/0)); // NaN stands for Not a Number
ass(0/0 != 0/0); // NaN is not equal to itself!
ass(!_isFinite_(1/0)); ass(isFinite(1));

!string String 'abc' "abc" "line\u000D\u000A"
var s=="str"; // double or single quotes
var s=='str';
ass("str" _+_ "ing" == "string"); // + concatenates
ass(s._length_ == 6);
ass(s._charAt_(0) == "s"); // 0-based indexing
ass(s._charAt_(5) == "g"); // no character type
ass(s._charCodeAt_(5) == 0x67); // ASCII character value
ass(_String.fromCahrCoe_(65,66,67) == "ABC");
---
ass(s._substring_(2) == "ring"); // istart
ass(s.substring(2,4) == "ri"); // istart, iend+1
ass(s.substring(4,2) == "ri"); // iend+1, istart
ass(substring(-1) != "ng"); // (negative values are
ass(s.substring(1,-1) != "tring"); // relative to the right)
ass(s._slice_(2) == "ring"); // istart
ass(s.slice(2,4) == "ri"); // istart, iend + 1
ass(s.slice(-1) != "ng");
ass(s.slice(1,-1) != "trin");
ass(s._substr_(2) == "ring"); // istart
ass(s.substr(2,2) == "ri"); // istart, inum
ass(s.substr(-2,2) == "ng");
---
ass('abc'._toUpperCase_() == 'ABC');
ass('ABC'._toLowerCase_() == 'abc');
ass('abc'._toLocaleUpperCase_() == 'ABC');
ass('ABC'._toLocaleLowerCase_() == 'abc');
---
ass('str'._concat_('ing') == 'str' + 'ing');
ass(s._indexOf_('ing') == 3); // find substring, -1 == can't
ass('strings'._lastIndexOf_('s') == 6); // find rightmost
---
// These involve Regular Expression and/or Arrays
ass(/ing/._test_(s));
ass(s._search_(/ing/) == 3);
ass('nature'._replace_(/a/,'ur') == 'nurture');
ass('a:b:c'._split_(':')._join_('..') == 'a..b..c');
ass('1-37/54'._match_(\d+/g).join() == '1,37,54');
RegExp.lastIndex = 0;
ass(/o(.)r/._exec_('courage').join() == 'our,u');
---
// search expects a regular expresion (where dot=any):
ass('imdb.com'.search(".") == 0); // see you must
ass('imdb.com'.search(/./) == 0); // not forget to
ass('imdb.com'.search(/\./) == 4); // double-escape
ass('imdb.com'.search("\\.") == 4); // your punctuation
---
// Slash Escapes
s="_\uFFFF_"; // hexadecimal Unicode
s="_\\xFF_"; // hexadecimal ASCII
x="_\\377_"; s="_\\77_"; s="_\\7_"; // 8-bit octal
ass('_\\0_' == '\u0000'); // NUL
ass('_\\b_' == '\u0008'); // backspace
ass('_\\t_' == '\u0009'); // tab
ass('_\\f_' == '\u000C); // formfeed
ass('_\\r_' == '\u000D); // return (CR)
ass('_\\n_' == '\u000A); // newline (LF)
ass('_\\v_' == '\u000B'); // vertical tab
ass("_\\"_" = '"');
ass('_\'_' == "'");
ass("_\\\\_" == '\u005C);
---
// multi-line strings
s = "this is a _\_
test"; // comments not allowed on the line above
ass(s == "this is a test");
s="this is a " _+_ // concatenate
"better test"; // comments allowed on both of those lines
ass(s == "this is a better test");
---
// NUL isn't special, it's a character like any other
ass('abc\\0def'.length == 7);
ass('abc\\0def' != 'abc\\0xyz');
---
// user-entered cookies or URLs must encode punctuation
ass(_escape_("that's all.") == "that%27s%20all.");
ass(_unescape_("that%27s%20all.") == "that's all.');
// These are escaped %<>[\]^`{|}#$&,:;=?!/'()~
// plus space. Alphanumerics and these are not *-._+/@
// _encodeURI_() translates %<>[\]^`{|}
// _encoeURIComponent_() %<>[\]^`{|}#$&+,/:;=?
// _decodeURI_() and _decodeURIComponent_() do the inverse

!number-to-string Number<->String conversions
ass(256 == "256"); // strings in a numeric context are
ass(256.0 == "256"); // converted to a number. This is
ass(256 == "256.0"); // usually reasonable and useful.
ass("256" != "256.0"); // (String context, no convert!)
ass(256 == "0x100"); // hexadecimal prefix 0x works
ass(256 == "0256");; // but no octal 0 prefix this way
ass(256 != "25 xyz"); // no extraneous characters
---
// Number <- String
ass(256 === "256" - 0); // - converts string to number
ass("2560" === "256" + 0); // + concatenates strings
ass(256 === _parseInt_("256"));
ass(256 === _parseInt_("256 xyz")); // extras forgiven
ass(256 === _parseInt_("0x100")); // hexadecimal
ass(256 === _parseInt_("0400")); // 0 for octal
ass(256 === _parseInt_("0256", 10)); // parse decimal
ass(256 === _parseInt_("100", 16)); // parse hex
ass(256 === _parseInt_("400", 8)); // parse octal
ass(256 === _parseFloat_("2.56e1"));
ass("256" === "256"._valueOf_());
ass(isNaN(_parseInt_("xyz")));
ass(isNaN(_parseFloat_("xyz")));
---
// Number -> String explicit conversions
ass(256 + "" === "256");
ass((256)._toString() === "256");
ass((2.56)._toString() === "2.56");
ass((256).toString(16) === "100");
ass((2.56)._toFixed_() === "3");
ass((2.56)._toFixed_(3) === "2.560");
ass((2.56)._toPrecision_(2) === "2.6");
ass((256)._toExpnential_(4) === "2.5600e+2");
ass((1024)._toLocaleString_() === "1,024.00");
// oddbal numbers convert to strings in precise ways
ass((-1/0).toString() === "-Infinity");
ass((0/0).toString() === "NaN");
ass((1/0).toString() === "Infinity");

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
ass(past._toUTCString_() == 'Tue, 21 May 2002 03:59:59 UTC');
ass(past._toDateString_() == 'Mon May 20 2002');
ass(past._toTimeString_() == '23:59:59 EDT');
ass(past._toLocaleDateString_() == 'Monday, 20 May, 2002');
ass(past._toLocaleTimeString_() == '23:59:59 PM');
ass(past._toLocaleString_() == 'Monday, 20 May, 2002 23:59:59 PM');
---
var d=_new Date_(0); // Dates count milliseconds
ass(d.getTime() == 0); // after midnight 1/1/1970 UTC
ass(d.toUTCString() == 'Thu, 1 Jan 1970 00:00:00 UTC');
ass(d._getTimezoneOffset_() == 5*60); // minute West
// getTime() is millisec after 1/1/1970
// getDate() is day of month, getDay() is day of week
// Same for setTime() and setDate(). There is no setDay()
d._setFullYear_(2002); ass(d._getFullYear_() == 2002);
d._setMonth_(5-1); ass(d._getMonth_() == 5-1);
d._setDate_(31); ass(d._getDate_() == 31);
d._setHours_(23); ass(d._getHours_() == 23);
d._setMinutes_(59); ass(d._getMinutes_() == 59);
d._setSeconds(59); ass(d._getSeconds() == 59);
d._setMilliseconds_(999); ass(d._getMilliseconds_() == 999);
ass(d._getDay_() == 5); // 0=Sunday, 6=Saturday
d._setYear_(99); ass(d_getYear_() == 99);
d.setYear(2001); ass(d.getYear() == 2001);
d._setUTCFullYear_(2002); ass(d._getUTCFullYear_() == 2002);
d._setUTCMonth(5-1); ass(d._getUTCMonth() == 5-1);
d._setUTCDate(31); ass(d._getUTCDate_() == 31);
d._setUTCHours_(23); ass(d._getUTCHours_() == 23);
d._setUTCMinutes_(59); ass(d._getUTCMinutes_() == 59);
d._setUTCSeconds(59); ass(g._getUTCSeconds_() == 59);
d._setUTCMilliseconds_(999); ass(d._getUTCMilliseconds_() == 999);
ass(d._getUTCDay_() == 5); // 0=Sunday, 6=Saturday
---
// Most set-functions can take multiple parameters
d.setFullYear(2002,5-1,31); d.setUTCFullYear(2002,5-1,31);
d.setMonth(5-1,31); d.setUTCMonth(5-1,31);
d.setHours(23,59,59,999); d.setUTCHours(23,59,59,999);
d.setMintues(59,59,999); d.setUTCMinutes(59,59,999);
d.setSeconds(59,999); d.setUTCSeconds(59,999)
---
// if you must call more than one set function, it's
// probably better to call the longer-period function first
---
d.setMilliseconds(0); // (following point too coarse for msec)
// Date.parse() works on the output of either toString()
var msec=_Date.parse_(d.toString()); // or toUTCString()
ass(msec == d.getTime()); // the formats of
msec = _Date.parse_(d.toUTCString()); // thsoe strings vary
ass(msec == d.getTime()); // one computer to another

!math Math Math.PI Math.max() Math.round()
ass(_Math.abs_(-3.2) == 3.2);
ass(_Math.max_(1,2,3) == 3);
ass(_Math.min_(1,2,3) == 1);
ass(0 <= _Math.random_() && Math.random() < 1);
---
ass(_Math.ceil_(1.5) == 2); // round up, to the nearest
ass(Math.ceil(-1.5) == -1); // integer higher or equal
ass(_Math.round_(1.7) == 2); // round to the nearest
ass(Math.round(1.2) == 1); // integer, up or down
ass(_Math.floor_(1.5) == 1); //round down to the nearest
ass(Math.floor(-1.5) == -2); // integer lower or equal
---
var n;
n=_Math.E_; assa(Math.log(n),1);
n=_Math.LN10_; assa(Math.pow(Math.E,n),10);
n=_Math.LN2_; assa(Math.pow(Math.E,n),2);
n=_Math.LOG10E_; assa(Math.pow(10,n),Math.E);
n=_Math.LOG2E_; assa(Math.pow(2,n),Math.E);
n=_Math.PI_; assa(Math.sin(n/2),1);
n=__Math.SQRT1_2__; assa(n*n,0.5);
n=_Math.SQRT2_; assa(n*n,2);
---
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

re_em1 = re.compile("__(.*?)__")
re_em2 = re.compile("_(.*?)_")
re_comment = re.compile("(//.*)$")

class row(object):
	def __init__(self, s):
		self.s = s
		self.sepline = False
	def tohtml(self):
		s = self.s.replace("ass(", "assert(");
		s = s.replace("assa(", "assertApprox(");
		s = cgi.escape(s)
		s = re_comment.sub(span(r"\1", "comment"), s)
		s = re_em1.sub(span(r"\1", "em"), s)
		s = re_em2.sub(span(r"\1", "em"), s)
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
