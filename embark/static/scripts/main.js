function navToolTip() {
    let menuBtn = document.querySelector("#menuBtn");
    let navigation = document.querySelector(".navigation");

    menuBtn.onclick = function () {
        navigation.classList.toggle("active");
    }

}

function expertModeOn() {
    /*
    Function to enable the expertmode and show hidden expert mode fields in forms
    */
    try {
        var expertOptions = document.querySelectorAll('[value="expmode"]');

        for (i = 0; i < expertOptions.length; i++) {
            var expertDiv = expertOptions[i];
            if (expertDiv.style.display === "none") {
                expertDiv.style.display = "block";
            } else {
                expertDiv.style.display = "none";
            }
        }
    } catch (error) {
        errorAlert(error.message);
    }
}

function helpTextOn() {
    /*
    Function to display the individual helptext of form fields below
    */
    try {
        var expertOptions = document.querySelectorAll('[value="help_text"]');

        for (i = 0; i < expertOptions.length; i++) {
            var expertDiv = expertOptions[i];
            if (expertDiv.style.display === "none") {
                expertDiv.style.display = "block";
            } else {
                expertDiv.style.display = "none";
            }
        }
    } catch (error) {
        errorAlert(error.message);
    }
}


function confirmDelete(event) {
    /*
    Function to show a window on confirmation screen asking the user to progress
    */
    var isValid = confirm(`Are you sure to delete the following firmware file: ${event.target.elements.firmware.value} ?`);
    if (!isValid) {
        event.preventDefault();
        errorAlert("deletion cancelled");
    } else {
        successAlert(`firmware file deleted: ${event.target.elements.firmware.value}`);
    }
}