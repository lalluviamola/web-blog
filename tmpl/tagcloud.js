<script type="text/javascript">

function showLogin() {
    $('#login_id').removeClass("invisible").addClass("visible");
}

function hideLogin() {
    $('#login_id').removeClass("visible").addClass("invisible"); 
}

var articles_json = null;
var TAGS_IDX = 3;

function a(url, txt) {
  return '<a href="' + url + '">' + txt + "</a>";
}
function span(txt, cls) {
  return '<span class="' + cls + '">' + txt + '</span>';
}

function tagUrl(url, tag, count) {
  return span(a(url, tag) + ' ' + span('(' + count + ')', "light"), "nowrap") + ' ';
}

function genTagCloudHtml() {
  var all_tags = {};
  var all_tags_arr = [];
  var tag, tags;
  var tag_count;
  var i, j;
  var lines = [];

  for (i=0; i < articles_json.length; i++) {
    tags = articles_json[i][TAGS_IDX];
    for (j=0; j < tags.length; j++) {
      tag = tags[j];
      tag_count = all_tags[tag];
      if (undefined == tag_count) {
        tag_count = 1;
      } else {
        tag_count += 1;
      }
      all_tags[tag] = tag_count;
    }
  }

  for (tag in all_tags) {
    all_tags_arr.push(tag);
  }

  all_tags_arr.sort(function(x,y){ 
      var a = String(x).toUpperCase(); 
      var b = String(y).toUpperCase(); 
      if (a > b) 
         return 1 
      if (a < b) 
         return -1 
      return 0; 
    });
  lines.push(tagUrl("/archives.html", "all", articles_json.length));
  for (i = 0; i < all_tags_arr.length; i++) {
    tag = all_tags_arr[i];
    tag_count = all_tags[tag];
    lines.push(tagUrl("/tag/" + tag, tag, tag_count));
  }
  return lines.join("");
}
</script>
