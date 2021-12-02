// jshint unused:false
// ^ this should only be added AFTER successfull check (disables warning for global functions)

/**
 * Activate Navigation Menu
 */
function navToggle() {
    "use strict";
    document.getElementById("navigation").classList.toggle("active");
}

/**
 * To display the individual helptext of form fields below
 */
 function helpTextOn() {
    "use strict";
    try {
        var expertOptions = document.querySelectorAll('small.text-muted');

        for (var i = 0; i < expertOptions.length; i++) {
            var expertDiv = expertOptions[i];
            if (expertDiv.getAttribute("value") === "help_text_off") {
                expertDiv.setAttribute("value","help_text_on");
            } else {
                expertDiv.setAttribute("value","help_text_off");
            }
        }
    } catch (error) {
        console.log(error.message);
    }
}

/**
 * To toggle expert mode option during analysing the Firmware
 */
function expertModeOn() {
    "use strict";
    try {
        var expertOptions = document.querySelectorAll('div.expertModeOptions');

        for (var i = 0; i < expertOptions.length; i++) {
            var expertDiv = expertOptions[i];
            if (expertDiv.getAttribute("value") === "expmode_off") {
                expertDiv.setAttribute("value","expmode_on");
            } else {
                expertDiv.setAttribute("value","expmode_off");
            }
        }
    } catch (error) {
        console.log(error.message);
    }
    /* we enable the help text automatically in expert mode */
    helpTextOn();
}

/**
 * To show a window on confirmation screen asking the user to progress
 * @param {*} event Event Object which provides the firmware Value
 */
function confirmDelete(event) {
    "use strict";
    var isValid = confirm(`Are you sure to delete the following firmware file: ${event.target.elements.firmware.value} ?`);
    if (!isValid) {
        event.preventDefault();
          console.log("deletion cancelled");
    } else {
        successAlert(`firmware file deleted: ${event.target.elements.firmware.value}`);
    }
}
