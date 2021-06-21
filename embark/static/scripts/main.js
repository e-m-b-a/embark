// function includeHTML() {
//     var z, i, elmnt, file, xhttp;
//     /*loop through a collection of all HTML elements:*/
//     z = document.getElementsByTagName("*");
//     for (i = 0; i < z.length; i++) {
//         elmnt = z[i];
//         /*search for elements with a certain atrribute:*/
//         file = elmnt.getAttribute("w3-include-html");
//         if (file) {
//             /*make an HTTP request using the attribute value as the file name:*/
//             xhttp = new XMLHttpRequest();
//             xhttp.onreadystatechange = function () {
//                 if (this.readyState == 4) {
//                     if (this.status == 200) {
//                         elmnt.innerHTML = this.responseText;
//                     }
//                     if (this.status == 404) {
//                         elmnt.innerHTML = "Page not found.";
//                     }
//                     /*remove the attribute, and call this function once more:*/
//                     elmnt.removeAttribute("w3-include-html");
//                     includeHTML();
//                 }
//             }
//             xhttp.open("GET", file, true);
//             xhttp.send();
//             /*exit the function:*/
//             return;
//         }
//     }
// }

// function uploader() {
//     try {
//         $.ajax({
//             url: "upload/",
//             datatype: "html",
//             type: "GET",
//             success: function (data) {
//                 document.getElementById("uploader").innerHTML =
//                     data;
//             }
//         });
//     } catch (error) {
//         alert(error.message);
//     }
// }

// function loadServiceDasboard() {
//     try {
//         $.ajax({
//             url: "serviceDashboard/",
//             datatype: "html",
//             type: "GET",
//             success: function (data) {
//                 document.getElementById("service").innerHTML =
//                     data;
//             }
//         });
//     } catch (error) {
//         alert(error.message);
//     }
// }

//function loadReportDashboard() {
//    try {
//        $.ajax({
//            url: "reportDashboard/",
//            datatype: "html",
//            type: "GET",
//            success: function (data) {
//                document.getElementById("reports").innerHTML =
//                    data;
//            }
//        });
//    } catch (error) {
//        alert(error.message);
//    }
//}

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
        alert(error.message);
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
        alert(error.message);
    }
}


function confirmDelete(event) {
    /*
    Function to show a window on confirmation screen asking the user to progress
    */
    var isValid = confirm(`Are you sure to delete the following firmware file: ${event.target.elements.firmware.value} ?`);
    if (!isValid) {
        event.preventDefault();
        alert("deletion cancelled");
    } else {
        alert(`firmware file deleted: ${event.target.elements.firmware.value}`);
    }
}