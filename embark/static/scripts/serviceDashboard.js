// jshint unused:false
// ^ this should only be added AFTER successfull check (disables waring for global functions)

/**
 * Update the Progress bar with the percentange of progress made in Analysing the Firmware
 * @param {*} percent Percentage Completed
 * @param {*} cur_ID Current Id of the Container
 */
 function makeProgress(percent, cur_ID) {
    "use strict";
    var rounded = Math.round(percent);
    var id = "#pBar_" + cur_ID;
    $(id).attr('aria-valuenow', rounded).css('width', rounded + '%').text(rounded + '%');
}

/**
 * Bind the Phase Messages from log file to Container
 * @param {*} phase_list list of Phase Messages received from Log
 * @param {*} cur_ID Current Id of the Container
 */
function livelog_phase(phase_list, cur_ID) {
    "use strict";
    var id = "#log_phase_" + cur_ID;
    var $List = $(id);
    $List.empty()
    for (const phase_ in phase_list){
        var $entry = $('<li>' + phase_ + '</li>');
        $List.append($entry);
    }
}

/**
 * Bind the Module message_list from log file to container
 * @param {*} module_list list Module Log message received from Log
 * @param {*} cur_ID Current Id of the container
 */
function livelog_module(module_list, cur_ID) {
    "use strict";
    var id = "#log_module_" + cur_ID;
    var $List = $(id);
    $List.empty()
    for (const module_ in module_list){
        var $entry = $('<li>' + module_ + '</li>');
        $List.append($entry);
    }
}

function getCookie(name) {
    "use strict";
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
  
/**
 * Removes the container from the UI
 * @param {*} currentID Id of the container which is passed backend to pull information
 */
function cancelLog(currentID) {
    "use strict";
    try {
        var idOfDIV = "#Container_" + currentID;
        $(idOfDIV).remove();
    } catch (error) {
        //console.log(error.message);
        console.log(error);
    }
}

/**
 * simple redirect to hashid associated with currentID
 * @param {*} currentID Id of the contaniner which is passed backend to pull information
 */
 function viewLog(currentID) {
    "use strict";
    try {
        // TODO get hashid of div-id
        window.location("/log/" + currentID);
    } catch (error) {
        //console.log(error.message);
        console.log(error);
    }
}

/**
 *  start socket connection just once TODO wss compatible? 
 */
var loc = window.location;
var wsStart = 'ws://';
var wsPort = ':8001';
if (loc.protocol == 'https:') {
      wsStart = 'wss://';
      wsPort = ':8000';
}
var socket = new WebSocket(
        wsStart + location.hostname + wsPort + '/ws/progress/'
);
/*for log implementation which is currently commented out*/
var module_array = [];
var phase_array = [];
var cur_len = 0;

/**
 * called when a websocket connection is established
 * */
socket.onopen = function () { 
    "use strict";
    console.log("[open] Connection established");
    socket.send("Reload");
};

/**
 * This method is called whenever a message from the backend arrives
 * */
socket.onmessage = function (event) {
    "use strict";
    console.log("Received a update");
    var data = JSON.parse(event.data);
    try{
        // for analysis in message create container
        for (const analysis_ in data){
            //create container if new analysis
            var newContainer = document.getElementById("Container_" + data[analysis_].analysis);
            if (newContainer == null) {
                var htmlToAdd = `
                    <div class="box" id="Container_` + data[analysis_].analysis + `">
                        <div class="mainText">
                            <span>`+ data[analysis_].firmware_name.split(".")[0]+`</span>
                        </div>
                        <div class="row">
                            <div class="col-sm log tile moduleLog">
                                <ul class="log_phase logUL" id="log_phase_` + data[analysis_].analysis + `"></ul>
                            </div>
                            <div class="col-sm log tile phaseLog">
                                <ul class="log_phase logUL" id="log_module_` + data[analysis_].analysis + `"></ul>
                            </div>
                        </div>
                        <div id="progress-wrapper">
                            <div id="pBar_` + data[analysis_].analysis + `" class="progress-bar" role="progressbar" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                                    0 % 
                            </div>
                        </div>
                    </div>
                    <div class="buttonRow">
                        <!--
                        <button type="view-log" class="btn buttonRowElem" id="` + data[analysis_].analysis + `" onclick="viewLog(this.id)" >
                            EMBA-log
                        </button>
                        <button type="reset" class="btn buttonRowElem" id="` + data[analysis_].analysis + `" onclick="cancelLog(this.id)" >
                            Cancel
                        </button>
                        -->
                    </div>`;
            document.getElementsByClassName("main")[0].insertAdjacentHTML('beforeend', htmlToAdd);
            }
            // append phase and module arrays
            console.log("log_phase_" + data[analysis_].analysis);
            livelog_module(data[analysis_].module_list, data[analysis_].analysis)
            livelog_phase(data[analysis_].phase_list, data[analysis_].analysis)
            // set percentage and other metadata
            // TODO add metasinfo
            makeProgress(data[analysis_].percentage, data[analysis_].analysis)
        }
    }
    catch(error){
        console.log(error);
    }
};

/**
 * This method is called when the websocket connection is closed
 *  */
socket.onclose = function () {
    "use strict";
    // console.error('Chat socket closed unexpectedly', event);
    console.log("[Socket]Closed Successfully");
};

/**
 * this method is called when an error occurs
 *  */
socket.onerror = function (err) {
    "use strict";
    //console.error('Socket encountered error: ', err.message, 'Closing socket');
    console.error('Socket encountered error: ', err);
    socket.close();
};

/* /**
 * Connection Established
 
function embaProgress() {
    console.log("Messaging started")
    setInterval(function () {
        socket.send("Hello");
    }, 3000);
}
 */

