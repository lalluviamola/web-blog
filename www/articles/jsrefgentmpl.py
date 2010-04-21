tmpl = """<html>
<head>
<style type="text/css">

body, table {
	font-family: "Lucida Grande", sans-serif;
	font-size: 12px;
}

table {
	color: #444;
}

td {
	font-family: consolas, menlo, monospace;
}

.header {
	color: #420066;
	font-style: italic;
}

.line {
	border-bottom: 1px dotted #ccc;
}

.big {
	font-size: 140%;
	font-weight: bold;
}

.comment {
	color: #999;
}

.em {
	font-weight: bold;
	color: #420066;
	font-size: 130%;
}

</style>
</head>
<body>

<div>
    <a href="/index.html">home</a> &#8227;
	quick links: <a href="#number">Number</a> &bull;
	<a href="#string">String</a> &bull;
	<a href="#number-to-string">Number&lt;-&gt;String</a> &bull;
	<a href="#boolean">Boolean</a> &bull;
	<a href="#date">Date</a> &bull;
	<a href="#math">Math</a> &bull;
	<a href="#array">Array</a> &bull;
	<a href="#function">Function</a> &bull;
	<a href="#logic">logic</a> &bull;
	<a href="#object">Object</a> &bull;
	<a href="#type">type</a> &bull;
	<a href="#object-orientation">object-orientation</a> &bull;
	<a href="#exceptions">exceptions</a>
</div>
<br>
%s

<hr/> 
<center><a href="/index.html">Krzysztof Kowalczyk</a></center> 

<script type="text/javascript">
  var _gaq = _gaq || [];
  _gaq.push(['_setAccount', 'UA-194516-1']);
  _gaq.push(['_trackPageview']);

  (function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    (document.getElementsByTagName('head')[0] || document.getElementsByTagName('body')[0]).appendChild(ga);
  })();
</script>

</body>
</html>"""
