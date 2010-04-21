tmpl = """<html>
<head>
<style type="text/css">

body, table {
	font-family: "Lucida Grande", sans-serif;
	font-size: 12px;
}

table {
	//border-bottom: 2px solid #ccc;
	color: #444;
}

td {
	font-family: consolas, monospace;
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
	font-size: 120%;
}

</style>
</head>
<body>

<div>
	Quick links: <a href="#number">Number</a>, 
	<a href="#num-2-str">Number&lt;-&gt;String</a>,
	<a href="#string">String</a>,
	<a href="#date">Date</a>,
	<a href="#boolean">Boolean</a>,
	<a href="#array">Array</a>,
	<a href="#function">Function</a>
</div>
<br>
%s
</body>
</html>"""
