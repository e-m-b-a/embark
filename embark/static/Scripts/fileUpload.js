/*Event Which is Responsible for the action after you drag and drop the files from your local folder*/
function fileDropEventHandler(ev) {
    for (let index = 0; index < ev.dataTransfer.items.length; index++) {
        let file = ev.dataTransfer.items[index].getAsFile();
        saveFile(file);
    }
}

/* The following event calls prevent default to turn off the browsers default drag and drop handler */
function dragOverHandler(ev) {
  ev.preventDefault();
}

/* The following event handles the upload of a file*/
function fileUpload(filesUploaded){
  for (let index = 0; index < filesUploaded.lastElementChild.files.length; index++) {
    let file = filesUploaded.lastElementChild.files[index];
    saveFile(file); 
  }
}

/** This function saves the file to local directory. */
async function saveFile(fileData){

      let formData = new FormData();
      formData.append("file",fileData);
      alert(fileData.name);
  }


  
  