
/* The following event calls prevent default to turn off the browsers default drag and drop handler */
function dragOverHandler(ev) {
  ev.preventDefault();
}

/** This function saves the file to local directory. */
/* fileData - Information of the uploaded file or Files*/
async function saveFiles(fileData){
  try {
    var formData = new FormData()
    for (let index = 0; index < fileData.length; index++) {
      formData.append('file',fileData[index]);
    }
      formData.append('file',fileData);
      $.ajax({
        type: 'POST',
        url:  'upload/save_file',
        data: formData,
        processData: false,
        contentType: false,
        success: function(data) {
            alert(""+data);
        }
    }); 
    } catch(error){
        alert(error.message);
    }
  }

  function saveDataFields(){
    try {
      var x = document.forms["dataFields"]["version"].value;
      if (x == "") {
         alert("Enter the version");
    }
    }catch (error) {
      alert(error.message);
    }
  }
  



  
  