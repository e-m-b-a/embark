function uploader() {
    try {
        $.ajax({
            url: "upload/",
            datatype: "html",
            type: "GET",
            success: function (data) {
                document.getElementById("uploader").innerHTML =
                    data;
            }
        });   
    }catch (error) {
        alert(error.message);   
    }
    
}

function expertModeOn() {
    try {
            var expertDiv = document.getElementById("expertOptions");
        if (expertDiv.style.display === "none") {
            expertDiv.style.display = "block";
        } else {
            expertDiv.style.display = "none";
        }
    } catch (error) {
        alert(error.message);
    }
    
}