$(document).ready(function(){
  $(".resultslink").click(function(){
    $("div#"+this.id+".results").slideToggle("slow");
  });
});

$(window).load(function() {
  $("div.results").hide("fast");
});

