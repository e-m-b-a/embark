/* The following event calls prevent default to turn off the browsers default drag and drop handler */
function dragOverHandler(ev) {
  ev.preventDefault();
}

/** This function binds file name to div. */
function showFiles(fileData) {
  try {
    document.getElementById("uploadedFileNames").style.display = 'block';
    document.querySelector(".fileName").innerHTML = fileData[0].name;
    $("#uploadFirmware-btn").attr("disabled", false);

  } catch (error) {
    errorAlert(error.message);
  }
}

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

/** This function saves the file to local directory. */
/* fileData - Information of the uploaded file or Files*/
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
              //fileData.inputFileName=fileName;
              formData.append('file', myRenamedFile);
              postFiles(formData);
            }
          } else {
            errorAlert("The file is not saved");
            location.reload();
          }
        } else {
          successAlert("" + data);
          location.reload()
          //document.getElementById("uploadedFileNames").style.display = 'none';
          location.reload();
        }
      }
    });
  } catch (error) {
    errorAlert(error.message);
  }
}

function saveDataFields(e) {
  e.preventDefault();
  try {
    var docln = document.getElementById('firmwareDataForm').elements.length;
    console.log(docln)
    successAlert("form data saved successfully");
  } catch (error) {
    errorAlert(error.message);
  }
}