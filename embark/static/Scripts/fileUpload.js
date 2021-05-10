/* The following event calls prevent default to turn off the browsers default drag and drop handler */
function dragOverHandler(ev) {
  ev.preventDefault();
}

/** This function saves the file to local directory. */
/* fileData - Information of the uploaded file or Files*/
async function saveFiles(fileData) {
  try {
    var formData = new FormData()
    for (let index = 0; index < fileData.length; index++) {
      formData.append('file', fileData[index]);
    }
    formData.append('file', fileData);
    $.ajax({
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
      type: 'POST',
      url: 'upload/save_file',
      data: formData,
      processData: false,
      contentType: false,
      success: function (data) {
        alert("" + data);
      }
    });
  } catch (error) {
    alert(error.message);
  }
}

function saveDataFields() {
  try {
    var x = document.forms["dataFields"]["version"].value;
    if (x == "") {
      alert("Enter the version");
    }
  } catch (error) {
    alert(error.message);
  }
}