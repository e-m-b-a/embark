/* The following event calls prevent default to turn off the browsers default drag and drop handler */
function dragOverHandler(ev) {
  ev.preventDefault();
}

/** This function binds file name to div. */
function showFiles(fileData) {
  try {
    document.getElementById("uploadedFileNames").style.display = 'block';
    document.querySelector(".fileText").innerHTML = fileData[0].name

  } catch (error) {
    alert(error.message);
  }
}

/** This function saves the file to local directory. */
/* fileData - Information of the uploaded file or Files*/
async function saveFiles() {
  try {
    var fileData = document.getElementById('file-input').files;
    var formData = new FormData()
    for (let index = 0; index < fileData.length; index++) {
      formData.append('file', fileData[index]);
    }
    formData.append('file', fileData);
    $.ajax({
      type: 'POST',
      url: 'home/home/upload/save_file',
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
        alert("" + data);
        document.getElementById("uploadedFileNames").style.display = 'none';
      }
    });
  } catch (error) {
    alert(error.message);
  }
}

function saveDataFields(e) {
  e.preventDefault();
  try {
    var docln = document.getElementById('firmwareDataForm').elements.length;
    console.log(docln)
    alert("form data saved successfully");
  } catch (error) {
    alert(error.message);
  }
}