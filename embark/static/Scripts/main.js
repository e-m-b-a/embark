function uploader(){
$.ajax({
    url:"upload",
    datatype:"html",
    type: "POST",
    success: function(data) {
        console.log(data);
        $('#uploader').html(html);
    }
  });}