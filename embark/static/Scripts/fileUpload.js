/*Event Which is Responsible for the action after you drag and drop the files from your local folder*/
/**ev - Event information from the drag and drop of Files */
function fileDropEventHandler(ev) {
  try {
    for (let index = 0; index < ev.dataTransfer.items.length; index++) {
      let file = ev.dataTransfer.items[index].getAsFile();
      saveFile(file);
  }   
  } catch (error) {
    alert(error.message);
  }
    
}

/* The following event calls prevent default to turn off the browsers default drag and drop handler */
function dragOverHandler(ev) {
  ev.preventDefault();
}

/* The following event handles the upload of a file*/
/**file uploaded - Pased from the html to upload the file */
function fileUpload(filesUploaded){
  try{
    for (let index = 0; index < filesUploaded.lastElementChild.files.length; index++) {
      let file = filesUploaded.lastElementChild.files[index];
      saveFile(file); 
    }
  }catch (error) {
    alert(error.message);
  }
}

/** This function saves the file to local directory. */
/* fileData - Information of the uploaded file*/
async function saveFile(fileData){
  try {
    var formData = new FormData()
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
    var x = document.forms["dataFields"]["version"].value;
      if (x == "") {
         alert("Enter the version");
      return false;
  }
  }



  
  