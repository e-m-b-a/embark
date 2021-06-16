// TODO frontend is currently doing nothing with the data from backend. Merge this Branch with Ravi's work

// start socket connection just once
var socket = new WebSocket(
        'ws://'
        + location.hostname + ':8001'
        + '/ws/progress/'
);

// for log implementation which is currently commented out
var current_module = "no module"
var current_phase = "no phase"
var cur_len = 0

// called when a websocket connection is established
socket.onopen = function (e) {
    console.log("[open] Connection established");
};

// this method is called whenever a message from the backend arrives
socket.onmessage = function (event) {

    var data = JSON.parse(event.data);
    console.log(data);

    if(cur_len !== Object.keys(data).length){

        var htmlToAdd = '<div class="row"><div class="coldiv"><a class="tile row statusTile"><div class="row statusEMba"><div class="col-sm log tile moduleLog"><ul class="log_phase" id="log_phase'+ Object.keys(data)[cur_len] +'"> </ul></div><div class="col-sm log tile phaseLog"><ul class="log_phase" id="log_module'+Object.keys(data)[cur_len]+'"> </ul></div></div></a></div></div>'
        document.getElementById("add_to_me").insertAdjacentHTML('afterend',htmlToAdd);

        cur_len += 1
    }


    // if (current_phase !== data.phase) {
    //     //console.log(data.phase)
    //     livelog_phase(data.phase)
    // }
    // if (current_module !== data.module) {
    //     livelog_module(data.module)
    // }
    // current_phase = data.phase
    // current_module = data.module

    // makeProgress(data.percentage)
}

// this method is called when the websocket connection is closed
socket.onclose = function (event) {
    console.log(event.reason)
    console.error('Chat socket closed unexpectedly');
};

// this method is called when a error occurs
socket.onerror = function(err) {
    console.error('Socket encountered error: ', err.message, 'Closing socket');
    socket.close();
};

// TODO impement this method. -> send a refresh request once page is loaded
function embaProgress() {
    console.log("Messaging started")
    setInterval(function(){ socket.send("Hello"); }, 3000);
    // this method is called when the connection is established
}

// TODO make this work with Ravis changes
// method for progressBar progress
function makeProgress(percent) {
    var p = percent * 100;
    var rounded = p.toFixed(2);
    $('#pBar').attr('aria-valuenow', rounded).css('width', rounded + '%').text(rounded + '%')
}

//log the current phase live
function livelog_phase(phase) {
    var ul = document.getElementById("log_phase");
    var li = document.createElement("li");
    li.appendChild(document.createTextNode(phase));
    ul.appendChild(li);
}

//log current phase live
function livelog_module(module) {
    var ul = document.getElementById("log_module");
    var li = document.createElement("li");
    li.appendChild(document.createTextNode(module));
    ul.appendChild(li);
}
