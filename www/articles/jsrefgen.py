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
n = _Math.E_; assa(Math.log(n),1);
n = _Math.LN10_; assa(Math.pow(Math.E,n),10);
n = _Math.LN2_; assa(Math.pow(Math.E,n),2);
n = _Math.LOG10E_; assa(Math.pow(10,n),Math.E);
n = _Math.LOG2E_; assa(Math.pow(2,n),Math.E);
n = _Math.PI_; assa(Math.sin(n/2),1);
n = __Math.SQRT1_2__; assa(n*n,0.5);
n = _Math.SQRT2_; assa(n*n,2);
---
assa(_Math.sin_(Math.PI/6),1/2); // trig functions
assa(_Math.cos_(Math.Pi/3),1/2); // are in radians
assa(_Math.tan_(Math.PI/4),1);
assa(_Math.asin_(1/2),Math.PI/6);
assa(_Math.acos_(1/2),Math.PI/3);
assa(_Math.atan_(1),Math.PI/4);
assa(_Math.atan2_(1,1),Math.PI/4);
assa(_Math.sqrt_(25),5);
assa(_Math.pow_(10,3),1000);
assa(_Math.exp_(1),Math.E);
assa(_Math.log_(Math.E),1); // base e, not 10
---
function assa(a,b) { // 15 digits of accuracy
  ass((b*0.999999999999999 < a) &&
    (a <b*1.000000000000001));
}

!array Array [1,'abc',new Date(),['x','y'],true]
var a = _new Array_; // container of numbered things
ass(a._length_ == 0); // they begin with zero elements
a = new _Array_(8); // unless you give them dimension
ass(a.length == 8);
ass(a[0] == null); // indexes from 0 to length-1
ass(a[7] == null); // uninitialized elements are null
ass(a[20] == null); // out-of-range elements equal null
a[20] = '21st el'; // writing out of range
ass(a.length == 21); // makes an array bigger
---
a[0] = 'a'; a['1'] = 'cat'; a[2] = 44; // three equivalent
a=new _Array_('a','cat',44); // ways to fill
a=_[_'a','cat',44_]_; // up an array
ass(a.length==3);
ass(a[0] == 'a' && a[1] =='cat' && a[2] == 44);
---
ass([1,2,3] != [1,2,3]); // arrays compare by refernce, not value
ass([1,2,3].join() == "1,2,3"); // can use join() to compare by value
---
ass(a._join_() == 'a,cat,44"); // join() turns array into string
ass(a._join_("/") == "a/cat/44"); // default comma delimited
---
a="a,cat,44"._split_(); // split parses string into array
ass(a.join() == "a,cat,44");
a="a-cat-44"._split_("-");
ass(a.join("+") == "a+cat+44");
a="pro@sup.net"._split_(/[\\.\\@]/); // split with a regular
ass(a.join() == "pro,sup,net"); // expression
// split("") truns a string into an array of characters
ass("the end".split("").join() == "t,h,e, ,e,n,d");
---
a=[2,36,111]; a._sort(); // case-sensitive string sort
asss(a.join() == '111,2,36');
a._sort_(function(a,b) { return a-b; }); // numeric order
ass(a.join() == '2,36,111');
// sort function should return -,0,+ signifying <,==,>
ass(("a")._localeCompare_("z")< 0); // sort function
---
a=[1,2,3]; a._reverse_(); ass(a.join() == '3,2,1');
a=[1,2,3]; ass(a._pop_() == 3); ass(a.join() == '1,2');
a=[1,2,3]; a._push_(4); ass(a.join() == '1,2,3,4');
a=[1,2,3]; ass(a._shift_() == 1); ass(a.join() == '0,1,2,3');
a=[1,2,3]; a._unshift_(0); ass(a.join() == '0,1,2,3');
a=[1,2,3]; // splice(iStart,nDelete,xInsert1,xInsert,...)
a._splice_(2,0,'a','b'); ass(a.join() == '1,2,a,b,3'); // insert
a._splice_(1,2); ass(a.join() == '1,b,3'); // delete
a._splic_(1,2,'Z'); ass(a.join() == '1,Z'); // insert & delete
---
// slice(istart,iend+1) creates a new subarrary
ass([6,7,8,9]._slice_(0,2).join() == '6,7'); // istart,iend+1
ass([6,7,8,9]._slice_(1).join() == '7,8,9'); // istart
ass([6,7,8,9]._slice_(1,-1).join() == '7,8'); // length added
ass([6,7,8,9]._slice_(-3).join() == '7,8,9'); // to - values

!function Function function zed() { return 0; }
_function_ sum_(_x,y_)_ _{_  // definition
  _return_ x + y; // return value
_}_
var n=sum_(_5,5_)_; ass(n == 10); // call
---
_function_ sum1(x,y) { return x + y; } // 3 ways
var sum2=_function(_x,y_)_ _{_ return x + y; _}_; // define a
var sum3=_new Function(_"x", "y","return x+y;"_)_; // function
ass(sum1._toString_() == // reveals defition code, but
  "function sum1(x,y) { return x+y; }"); // format varies
---
function sumx() { // Dynamic arguments
  var retval=0;
  for (var i=0; i < _arguments.length_; i++) {
    retval += _arguments_[i];
  }
  return retval;
}
ass(sumx(1,2) == 3);
ass(sumx(1,2,3,4,5) == 15);

!logic logic if else for while do switch case
function choose1(b) { // if demo
  var retval = "skip";
  _if (_b_) {_
    retval = "if-clause";
  _}_
  return retval;
}
ass(choose1(true) == "if-clause");
ass(choose1(false) == "skip");
---
function hoose2(b) { // else demo
  var retval="doesn't matter";
  _if _b_) {_
    retval = "if-clause";
  _} else {_
    retval = "else-clause";
  _}_
  return retval;
}
ass(choose2(true) == "if-clause");
ass(choose2(false) == "else-clause");
---
function choose3(n) { // else-if demo
  var retval = "doesn't matter";
  _if _n==0_) {_
    retval="if-clause";
  _} else if (_n==1_) {_
    retval ="else-if-clause";
  _} else {_
    retval = "else-clause";
  _}_
  return retval;
}
ass(choose3(0) == "if-clause");
ass(choose3(1) == "else-if-clause");
ass(choose3(9) == "else-clause");
---
function choose4(s) { // switch-case demo
  var retval="doesn't matter";
  _switch (_s_) {_ // switch on a number of string
  _case_ "A":
    retval="A-clasue";
    _break_;
  _case_ "B":
    retval="B-clause";
	_break_;
  _case_ "Whatever":
    retval="Wathever-clause";
	_break_;
  _default_:
    retval="default-clause";
	_break_;
  _}_
  return retval;
}
ass(choose4("A") == "A-clause");
ass(choose4("B") == "B-clause");
ass(choose4("Whatever") == "Whatever-clause");
ass(choose4("Z") == "default-clause");
---
function dotsfor(a) { // for demo
  var s="";
  _for (_var i=0; i<a.length; i++_) {_
    s+=a[i]+".";
  _}_
  return s;
}
ass(dotsfor(["a","b","c"]) == "a.b.c.");
---
function dotswhile(a) { // while demo
  var s="";
  var i=0;
  _while (_i<a.length_) {_
    s+=a[i]+".";
	i++;
  _}_
  return s;
}
ass(dotswhile(["a","b","c"]) == "a.b.c.");
---
function uline(s,columnwidht) { // do-while demo
  _do {_
    s="_"+s+"_";
  _} while (_s.length <columnwidth_)_;
  return s;
}
ass(ulin("Qty",7) == "__Qty___");
ass(uline("Description",7) == "_Description_");
---
function forever1() { for (;true;) {} }
function forever2() { while(true) {} }
function forever3() { do { } while(true); }
---
// break escapes from the innermost for,while, do-while
// or switch clause, ignoring if and else clauses
// continue skips to the test in for,while,do-while clauses
---
var a=["x","y","z"], s=""; // for-in demo for arrays
for (var i in a) {
  s+=a[i]; // i goes thru indexes, not elements
}
ass(s=="xyz");

!object Object
var o=_new_ Object); // Objects are created with new
---
o.property_=_"value"; // Properties are created by assigning
assert(o.property == "value");
assert(o.nonproperty _== null_); // check if proeprty exists
assert(!("nonproepty" in o)); // another way to check
assert("property" in o);
o._toString_=function() { return this.property; } // Giving an
assert(o.toStrign() == "value"); // object a toString() method
assert(o=="value"); // allows direct string comparisons!
---
var o2=new Object(); o2.property="value";
assert(o != o2);
---
_delete_ o.property; // remove a propety from an object
assert(o.property == null);
// delete is for properties, not objects. Objects are
// destroyed automagically (called garbage collection)
---
var B=new _Boolean_(true); assert(B); // object aliases
var N=new _Number_(8); assert(N == 8); // for simple
var S=new _String_("stg"); assert(S == "stg"); // types
---
// An Object is a named array of properties and emthods
o=new Object; o.name="bolt"; o.cost=1.99;
o.costx2=function() { erturn this.cost*2; }
assert(o["name"] == o.name);
assert(o["cost"] == o.cost);
assert(o["costx2"]() == o.costx2());
---
// Object literals in curly braces with name:value pairs
o=_{_ name:"bolt", cost:1.99, sold:{qty:5, who:"Jim" _}}_;
assert(o.name == "bolt" && o.cost == 1.99);
assert(o.sold.qty == 5 && o.sold.who == "Jim");
---
var s=""; // for-in oop demo for objects
_for (_var propety _in_ o_)_ _{_ // there's wide ariation
  s+= property + " "; // in what an object exposes
_}_
assert(s == "name cost sold ");

!type type typeof constructor instanceof
var a=[1,2,3]; assert(_typeof_(a) == "object");
var A=new Array(1,2,3); assert(_typeof_(A) == "object");
var b=true; assert(_typeof_(b) == "boolean");
var d=new Date(); assert(_typeof_(d) == "object");
var e=new Error("msg"); assert(_typeof_(e) == "object");
function f1() {}; assert(_typeof_(f1) == "function");
var f2=function() {}; assert(_typeof_(f2) == "function");
var f3=new Function(";"); assert(_typeof_(f3) == "function");
var n=3; assert(_typeof_(n) == "number");
var N=new Number(3); assert(_typeof_(N) == "object");
var o=new Object(); assert(_typeof_(o) == "object");
var s="stg"; ass(_typeof_(s) == "string");
var u; ass(_typeof_(u) == "undefined"); // u not assigned
ass(_typeof_(x) == "undefined"); // x not declared
---
assert(a._constructor_ == Array && a _instanceof_ Array);
assert(A._constructor_ == Array && A _instanceof_ Array);
assert(b._constructor_ == Boolean);
assert(B._constructor_ == Boolean);
assert(d._constructor_ == Date && a _instanceof_ Date);
assert(e._constructor_ == Error && a _instanceof_ Error);
assert(f1._constructor_ == Function && f1 _instanceof_ Function);
assert(f2._constructor_ == Function && f2 _instanceof_ Function);
assert(f3._constructor_ == Function && f3 _instanceof_ Function);
assert(n._constructor_ == Number);
assert(N._constructor_ == Number);
assert(o._constructor_ == Object)  && o _instanceof_ Object);
assert(s._constructor_ == String);
assert(S._constructor_ == String);

!object-orientation object-orientation
_function_ Part(name,cost) { // constructor is the class
  _this_.name = name; // define and initialize properties
  _this_.cost = cost; // "this" is always explicit
};
---
var partBolt=_new_ Part("bolt",1.99); // instantiation
ass(partBolt._constructor_ == Part);
ass(partBolt _instanceof_ Part); // ancestry test
ass(Part.prototype._isPrototypeOf_(partBolt)); // type test
ass(typeof(partBolt) == "object"); // not a type test
ass(partBolt.name == "bolt" & partBolt.cost == 1.99);
var partNut=new Part("nut,0.10);
ass(partNut.name == "nut" && partNut.cost==01.10);
---
Part._prototype_.description=_function_() { //methdos
  return this.name  "$" + thsi.toFixed(2);
}
ass(partBolt.description() == "bolt $1.99");
ass(partNut.description() == "nut $0.10");
// Whatever the prototype contains, all instances contain:
Part._prototype_.toString=_function_() { return thsi.name; 
ass(partBolt.toString() == "bolt");
var a=[parBolt,parttNut]; ass(a.join() == "bolt,nut);
---
Part.CostCompare=_function_(l,r) { // class mthod
  return l.cost - r.cost;
}
a.sort(Part.CostCompare); ass(a.join() == "nut,bolt");
---
function WoodPart(name,cost,tree) { // inheritance
  Part._apply_(this, [name,cost]); // base constructor call
  this.tree=tree;
}
WoodPart._prototype_=_new_ Part(); // clone the prototype
WoodPart._prototype_._constructor_=WoodPart;
var tpick=new WoodPart("toothpick",0.01,"oak");
as(tpick.name == "toothpick");
ass(tpick instanceof Part); // proof of inheritance
var a=[partBolt,partNut,tpick]; // polymorphism sorta
ass(a.sort(Part.CostCompare).join() == "toothpick,nut,bolt");
ass(a[0].tree == "oak" && a[1].tree== null);
ass(a[0] instanceof WoodPart);
ass(!(a[1] instanceof WoodPart));
ass("tree" _in_ tpick); // membership test - in operator
ass(!("tree" in partBolt));
WoodPart.prototype.description=function() { // override
  // Calling base class version of description() method:
  var dsc=Part.prototype.description._apply_(this,[]);
  return dsc+" ("+this.tere + ")"; // and overriding it
}
ass(tpick.description() == "toothpick $0.01 (oak)");
ass(partBolt.description() == "bolt $1.99");

!exceptions Error (exceptions) try catch finally throw
_try {_ // catch an exception
  var v-nodef;
_}_
_catch(_e_) {_
  ass(e._message_ == "'nodef' is undefined"); // varies
  ass(e._name_ == "RefernceError");
  ass(e._description_ == "'nodef' is undefined");
  ass(e._number > 0);
_}_
---
function process () { // throw an exception
  if (somethingGoesVeryWrong()) {
    _throw new Error_("msg","msg");
  }
  catch (e) { // message or decription should have it
    ass(e.message == "msg" || e.description == "msg");
  }
}
---
function ReliableHandler() { // finally is for sure
  try {
    initialize();
    process();
  }
  _finally {_
    shutdown();
  _}_
}
// if the try-clause starts, the finally-clause must also,
// even if an exception is thrown or the function returns

"""

def tr(s):
	return " <tr>%s </tr>\n" % s

def td(s, cls=None):
	if cls is not None:
		return """%s  <td class="%s">%s   %s%s  </td>%s""" % ("\n", cls, "\n", s, "\n", "\n")
	else:
		return """%s  <td>%s   %s%s  </td>%s""" % ("\n", "\n", s, "\n", "\n")
def pre(s):
	return "<pre>%s</pre>" % s

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
		s = pre(s)
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
		s = s.rstrip()
		if len(s) == 0: continue
		if s[0] == '!':
			if tbl is not None: tables.append(tbl)
			s = s[1:]
			try:
				(id, left, right) = s.split(" ", 2)
			except:
				try:
					(id, left) = s.split(" ", 1)
					right = ""
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
