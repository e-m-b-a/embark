
/**
 * The following event calls prevent default to turn off the browsers default drag and drop handler
 * @param {*} ev Event
 */
function dragOverHandler(ev) {
  ev.preventDefault();
}

/**
 * This function binds file name to div.
 * @param {*} fileData File Data Uploaded
 */
function showFiles(fileData) {
  try {
    document.getElementById("uploadedFileNames").style.display = 'block';
    document.querySelector(".fileName").innerHTML = fileData[0].name;
    $("#uploadFirmware-btn").attr("disabled", false);

  } catch (error) {
    errorAlert(error.message);
  }
}

/**
 * Checks for any Multiple uploads and the Passes to save 
 */
function saveFiles() {
    var progressBar = document.getElementById("progress-wrapper");
    if (progressBar.style.display == "none") {
      progressBar.style.display = "block";
    } else {
      progressBar.style.display = "none";
    }
    var fileData = document.getElementById('file-input').files;
    var formData = new FormData()
    for (let index = 0; index < fileData.length; index++) {
      fileData[index].inputFileName = fileData[index].name;
      formData.append('file', fileData[index]);

    }
  postFiles(formData);
}

/**
 * Makes Ajax call and save files locally
 * @param {*} formData Information of the uploaded file or Files
 */
async function postFiles(formData) {
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

            $('#progressBar').attr('aria-valuenow', percent).css('width', percent + '%').text(percent + '%')
          }
        });
        return xhr;
      },
      success: function (data) {
        if (data == "File Exists") {
          var fileData = document.getElementById('file-input').files[0];
          var formData = new FormData()
          var res = confirm("A File with the same name exists ,Click ok to rename and save it");
          if (res == true) {
            var fileName = prompt("Please enter the new File name", fileData.inputFileName);
            if (fileName != null) {
              const myRenamedFile = new File([fileData], fileName);
              formData.append('file', myRenamedFile);
              postFiles(formData);
            }
          } else {
            errorAlert("The file is not saved");
            location.reload();
          }
        } else {
          successAlert("" + data);
          location.reload();
        }
      }
    });
  } catch (error) {
    errorAlert(error.message);
  }
}
