
/**
 * Activate Navigation Menu
 */
function navToolTip() {
    let menuBtn = document.querySelector("#menuBtn");
    let navigation = document.querySelector(".navigation");

    menuBtn.onclick = function () {
        navigation.classList.toggle("active");
    }

}


/**
 * To toggle expert mode option during analysing the Firmware
 */
function expertModeOn() {
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

/**
 * To display the individual helptext of form fields below
 */
function helpTextOn() {

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

/**
 * To show a window on confirmation screen asking the user to progress
 * @param {*} event Event Object which provides the firmware Value
 */
function confirmDelete(event) {
    
    var isValid = confirm(`Are you sure to delete the following firmware file: ${event.target.elements.firmware.value} ?`);
    if (!isValid) {
        event.preventDefault();
        errorAlert("deletion cancelled");
    } else {
        successAlert(`firmware file deleted: ${event.target.elements.firmware.value}`);
    }
}