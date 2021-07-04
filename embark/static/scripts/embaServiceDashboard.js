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

        var htmlToAdd = '<div class="row"><div class="coldiv"><a class="tile row statusTile"><div class="progress" id="progress-wrapper"><div id="pBar_'+ Object.keys(data)[cur_len] +'" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div><br><div class="row statusEMba"><div class="col-sm log tile moduleLog"><ul class="log_phase" id="log_phase_'+ Object.keys(data)[cur_len] +'"> </ul></div><div class="col-sm log tile phaseLog"><ul class="log_phase" id="log_module_'+Object.keys(data)[cur_len]+'"> </ul></div></div><button type="submit" class="btn" id="'+Object.keys(data)[cur_len]+'" onclick="pythonAjax(this.id)" >Upload</button></a></div></div>'
        document.getElementById("add_to_me").insertAdjacentHTML('afterend',htmlToAdd);

        cur_len += 1
    }
    if (current_phase !== data.phase) {
        //console.log(data.phase)
         livelog_phase(data.phase,Object.keys(data)[cur_len])
     }
    if (current_module !== data.module) {
         livelog_module(data.module,Object.keys(data)[cur_len])
     }
     current_phase = data.phase
     current_module = data.module

     makeProgress(data.percentage,Object.keys(data)[cur_len])
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
function makeProgress(percent,cur_ID) {
    var p = percent * 100;
    var rounded = p.toFixed(2);
    id = "#pBar_"+ cur_ID;
    $(id).attr('aria-valuenow', rounded).css('width', rounded + '%').text(rounded + '%')
}

//log the current phase live
function livelog_phase(phase,cur_ID) {
    var id = "log_phase_"+cur_ID;
    var ul = document.getElementById(id);
    var li = document.createElement("li");
    li.appendChild(document.createTextNode(phase));
    ul.appendChild(li);
}

//log current phase live
function livelog_module(module,cur_ID) {
    var id = "log_module_"+cur_ID;
    var ul = document.getElementById(id);
    var li = document.createElement("li");
    li.appendChild(document.createTextNode(module));
    ul.appendChild(li);
}


/**
 * 
 * @param {*} currentID Id of the contaniner which is passed backend to pull information
 */
function pythonAjax(currentID) {
    
    try {
        //formData.append('file', fileData);
        $.ajax({
          type: 'POST',
          url: 'function_Name',
          data: currentID,
          processData: false,
          contentType: false,
          success: function (data) {
            location.reload();
            }
          
        });
      } catch (error) {
        errorAlert(error.message);
      }
}
