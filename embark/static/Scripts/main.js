function uploader() {
    $.ajax({
        url: "upload/",
        datatype: "html",
        type: "GET",
        success: function (data) {
            console.log(data);
            document.getElementById("uploader").innerHTML =
                data;
            // $('#uploader').html(data);
        }
    });
    // fwdetails();
}

// function fwdetails() {
//     $.ajax({
//         url: "firmwaredetails/",
//         datatype: "html",
//         type: "GET",
//         success: function (data) {
//             console.log(data);
//             document.getElementById("details").innerHTML =
//                 data;
//         }
//     });

// }

function expertModeOn() {
    var x = document.getElementById("expertOptions");
    if (x.style.display === "none") {
        x.style.display = "block";
    } else {
        x.style.display = "none";
    }
}