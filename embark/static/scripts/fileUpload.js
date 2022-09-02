// jshint unused:false
// ^ this should only be added AFTER successful check (disables warning for global functions)
/**
 * The following event calls prevent default to turn off the browsers default drag and drop handler
 * @param {*} ev Event
 */
function dragOverHandler(ev) {
  "use strict";
  ev.preventDefault();
}

function getCookie(name) {
    "use strict";
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(window).bind("load", function() {
    "use strict";
    try{
        document.querySelector("#file-input").onchange = function(){
            var fileNames = "";
            for (var i = 0; i < this.files.length; i++) {
                fileNames = fileNames + this.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + "<br>";
            }
            var target = document.querySelector("#file-name");
            target.innerHTML = fileNames;
            $("#uploadFirmware-btn").attr("disabled", false);
        };
    }catch (error){
        console.log(error.message);
    }
});

/**
 * Makes Ajax call and save files locally
 * @param {*} formData Information of the uploaded file or Files
 */
 async function postFiles(formData) {
  "use strict";
  try {
    //formData.append('file', fileData);
    $.ajax({
      type: 'POST',
      url: '/uploader/save/',
      data: formData,
      headers: {
        'X-CSRFToken': getCookie('csrftoken')
      },
      processData: false,
      contentType: false,
      xhr: function () {
        var xhr = new window.XMLHttpRequest();

        xhr.upload.addEventListener('progress', function (e) {
          if (e.lengthComputable) {

            var percent = Math.round(e.loaded / e.total * 100);

            $('#progressBar').attr('aria-valuenow', percent).css('width', percent + '%').text(percent + '%');
          }
        });
        return xhr;
      },
      success: function (data) {
        if (data == "File Exists") {
          var fileData = document.getElementById('file-input').files[0];
          var formData = new FormData();
          var res = confirm("A File with the same name exists ,Click ok to rename and save it");
          if (res == true) {
            var fileName = prompt("Please enter the new File name", fileData.inputFileName);
            if (fileName != null) {
              const myRenamedFile = new File([fileData], fileName);
              formData.append('file', myRenamedFile);
              postFiles(formData);
            }
          } else {
            console.log("The file is not saved");
            errorAlert("" + data);
          }
        } else {
          if(data === "successful upload"){
            location.href = "";
          }
        }
      }
    });
  } catch (error) {
      console.log(error.message);
  }
}

/**
 * Checks for any Multiple uploads and the Passes to save
 */
function saveFiles() {
    "use strict";
    var progressBar = document.getElementById("progress-wrapper");
    if (progressBar.style.display == "none") {
      progressBar.style.display = "block";
    } else {
      progressBar.style.display = "none";
    }
    var fileData = document.getElementById('file-input').files;
    var formData = new FormData();
    for (let index = 0; index < fileData.length; index++) {
      fileData[index].inputFileName = fileData[index].name;
      formData.append('file', fileData[index]);
    }
  postFiles(formData);
}

