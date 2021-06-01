var socket;

function connect() {

    socket = new WebSocket(
        'ws://'
        + location.hostname + ':8001'
        + '/ws/progress/'
    );

    var current_module = "no module"
    var current_phase = "no phase"
    socket.onopen = function (e) {
        console.log("[open] Connection established");
    };

    // this method is called whenever a message from the backend arrives
    socket.onmessage = function (event) {

        var data = JSON.parse(event.data);
        console.log(data);
        if (current_phase !== data.phase) {
            //console.log(data.phase)
            livelog_phase(data.phase)
        }
        if (current_module !== data.module) {
            livelog_module(data.module)
        }
        current_phase = data.phase
        current_module = data.module

        makeProgress(data.percentage)
    }
    // this method is called when the websocket connection is closed

    socket.onclose = function (event) {
        console.log(event.reason)
        console.error('Chat socket closed unexpectedly');
        // setTimeout(function () {
        //     connect();
        // }, 1000);
    };

    socket.onerror = function(err) {
        console.error('Socket encountered error: ', err.message, 'Closing socket');
        socket.close();
    };
}

function embaProgress() {
    console.log("Maxi geht steil")

    setInterval(function(){ socket.send("Hello"); console.log("Maxi geht steiler"); }, 3000);
    // this method is called when the connection is established
}

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
