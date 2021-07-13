
/**
 *  start socket connection just once
 */
var socket = new WebSocket(
        'ws://'
        + location.hostname + ':8001'
        + '/ws/progress/'
);
/*for log implementation which is currently commented out*/
var module_array = []
var phase_array = []
var cur_len = 0

/**
 * called when a websocket connection is established
 * */ 
socket.onopen = function (e) {
    console.log("[open] Connection established");
};

/** 
 * This method is called whenever a message from the backend arrives
 * */ 
socket.onmessage = function (event) {

    try{
            var data = JSON.parse(event.data);
            console.log(data);

            if (cur_len !== Object.keys(data).length) {
                /* var htmlToAdd = '<div class="row"><div class="coldiv"><a class="tile row statusTile"><div class="progress" id="progress-wrapper"><div id="pBar_' + Object.keys(data)[cur_len] + '" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div><br><div class="row statusEMba"><div class="col-sm log tile moduleLog"><ul class="log_phase" id="log_phase_' + Object.keys(data)[cur_len] + '"> </ul></div><div class="col-sm log tile phaseLog"><ul class="log_phase" id="log_module_' + Object.keys(data)[cur_len] + '"> </ul></div></div><button type="submit" class="btn" id="' + Object.keys(data)[cur_len] + '" onclick="pythonAjax(this.id)" >Upload</button></a></div></div>' */
                var htmlToAdd = '<div class="row containerCSS" id="Container_' + Object.keys(data)[cur_len] + '"\n > <div class="title">\n <span>'+data[Object.keys(data)[cur_len]][0]["firmwarename"].split(".")[0]+'</span></div>\n<div class="row"><div class="col-sm log tile moduleLog"><ul class="log_phase logUL" id="log_phase_' + Object.keys(data)[cur_len] + '"> </ul > </div><div class="col-sm log tile phaseLog"><ul class="log_phase logUL" id="log_module_' + Object.keys(data)[cur_len] + '"> </ul></div></div><div class="row"><div class="progress col-sm-11" id="progress-wrapper"><div id="pBar_' + Object.keys(data)[cur_len] + '" class="progress-bar" role="progressbar" aria-valuenow: "0" aria - valuemin: "0"aria - valuemax= "100" > 0 % </div></div><div class="col-sm"><button type="submit" class="btn" id="' + Object.keys(data)[cur_len] + '" onclick="cancelLog(this.id)" >Cancel</button></div></div></div>'
                document.getElementById("add_to_me").insertAdjacentHTML('afterend', htmlToAdd);
                console.log("log_phase_" + Object.keys(data)[cur_len])
                module_array.push("no module");
                phase_array.push("no phase");
                cur_len += 1
            }

            for (let idx = 0; idx < cur_len; idx++) {
                let id = Object.keys(data)[idx]
                length = data[id].length
                if (phase_array[idx] !== data[id][length - 1].phase) {
                    console.log(data[id][length - 1].phase)
                    livelog_phase(data[id][length - 1].phase, id)
                }
                if (module_array[idx] !== data[id][length - 1].module) {
                    livelog_module(data[id][length - 1].module, id)
                }
                module_array[idx] = data[id][length - 1].module
                phase_array[idx] = data[id][length - 1].phase
                makeProgress(data[id][length - 1].percentage, id)
            }
    }
    catch(error){
        errorAlert(error.message);
    }
}

/**
 * This method is called when the websocket connection is closed
 *  */ 
socket.onclose = function (event) {
    console.log(event.reason)
    console.error('Chat socket closed unexpectedly');
};

/**
 * this method is called when a error occurs
 *  */ 
socket.onerror = function (err) {
    console.error('Socket encountered error: ', err.message, 'Closing socket');
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

/**
 * Update the Progress bar with the percentange of progress made in Analysing the Firmware
 * @param {*} percent Percentage Completed
 * @param {*} cur_ID Current Id of the Container
 */
function makeProgress(percent, cur_ID) {
    var p = percent * 100;
    var rounded = Math.round(p);
    id = "#pBar_" + cur_ID;
    $(id).attr('aria-valuenow', rounded).css('width', rounded + '%').text(rounded + '%')
}

/**
 * Bind the Phase Messages from log file to Container
 * @param {*} phase Phase Message received from Log
 * @param {*} cur_ID Current Id of the Container
 */
function livelog_phase(phase, cur_ID) {
    var id = "#log_phase_" + cur_ID;
    var $List = $(id);
    var $entry = $('<li>' + phase + '</li>');
    $List.append($entry);
}

/**
 * Bind the Module message from log file to container
 * @param {*} module Module Log message received from Log
 * @param {*} cur_ID Current Id of the container
 */
function livelog_module(module, cur_ID) {
    var id = "#log_module_" + cur_ID;
    var $List = $(id);
    var $entry = $('<li>' + module + '</li>');
    $List.append($entry);
}


/**
 * Removes the container from the UI
 * @param {*} currentID Id of the contaniner which is passed backend to pull information
 */
function cancelLog(currentID) {


    try {
        var idOfDIV = "#Container_" + currentID;
        $(idOfDIV).remove();
    } catch (error) {
        errorAlert(error.message);
    }
}