// jshint unused:false
// ^ this should only be added AFTER successfull check (disables waring for global functions)

/**
 * The following event calls prevent default to turn off the browsers default drag and drop handler
 * @param {*} ev Event
 */
function dragOverHandler(ev) {
  "use strict";
  ev.preventDefault();
}

$(window).bind("load", function() {
  "use strict";
  document.querySelector("#file-input").onchange = function(){
    var fileNames = "";
    for (var i = 0; i < this.files.length; i++) {
        fileNames = fileNames + this.files[i].name + "<br>";
    }
    var target = document.querySelector("#file-name");
    $.find(target).innerHTML = fileNames;
    $("#uploadFirmware-btn").attr("disabled", false);
  };
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
      url: 'save_file',
      data: formData,
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
            location.reload();
          }
        } else {
          /* location.reload(); */
          successAlert("" + data);
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

