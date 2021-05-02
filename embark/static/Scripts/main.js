function uploader(){
$.ajax({
    url:"upload/",
    datatype:"html",
    type: "GET",
    success: function(data) {
        console.log(data);
        document.getElementById("uploader").innerHTML =
        data;
        // $('#uploader').html(data);
    }
  });}

  function fwdetails(){
    $.ajax({
        url:"firmwaredetails/",
        datatype:"html",
        type: "GET",
        success: function(data) {
            console.log(data);
            document.getElementById("details").innerHTML =
            data;
        }
      });

  }