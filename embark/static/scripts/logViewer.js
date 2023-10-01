// jshint unused:false
// ^ this should only be added AFTER successfull check (disables waring for global functions)

/* global analysis_id */

window.addEventListener(
  "load",
  function () {
    "use strict";
    var loc = window.location;
    var wsStart = "ws://";
    var wsPort = ":8001";
    if (loc.protocol == "https:") {
      wsStart = "wss://";
      wsPort = ":8000";
    }

    var socket = new WebSocket(
      wsStart + location.hostname + wsPort + "/ws/logs/" + analysis_id
    );

    window.file_view = {
      offset: 0,
      limit: 50,
      content: "",
    };

    var logArea = document.getElementById("logArea");

    function onMessage(evt) {
      // There are two types of messages:
      // 1. a chat participant message itself
      // 2. a message with a number of connected chat participants
      var message = JSON.parse(evt.data);

      if (message.file_view) {
        var fileContent = atob(message.file_view.content) + "\u00a0"; // The nbsp is required in order to preserve trailing newlines
        logArea.textContent = fileContent;
        file_view = message.file_view;
      }
    }

    function onError(evt) {
      console.log("error", evt);
    }

    socket.onmessage = function (evt) {
      onMessage(evt);
    };

    socket.onerror = function (evt) {
      onError(evt);
    };

    function requestUpdate() {
      var requestView = Object.assign({}, file_view);
      requestView.content = "";
      socket.send(
        JSON.stringify({ action: "change_view", file_view: requestView })
      );
    }

    window.LogControls = {
      move_offset: function (lines) {
        file_view.offset += lines;
        requestUpdate();
      },
      set_offset: function (offset) {
        file_view.offset = offset;
        requestUpdate();
      },
      increase_view_size: function (lines) {
        file_view.limit += lines;
        if (file_view.limit < 5) {
          file_view.limit = 5;
        }
        if (file_view.num_lines != 0 && file_view.limit > file_view.num_lines) {
          file_view.limit = file_view.num_lines;
        }
        requestUpdate();
      },
    };

    function checkKey(e) {
      if (e.shiftKey) {
        if (e.keyCode == "38") {
          // Arrow Up
          window.LogControls.increase_view_size(1);
          e.preventDefault();
        } else if (e.keyCode == "40") {
          // Arrow Down
          window.LogControls.increase_view_size(-1);
          e.preventDefault();
        } else if (e.keyCode == "33") {
          // Page Up
          window.LogControls.increase_view_size(5);
          e.preventDefault();
        } else if (e.keyCode == "34") {
          // Page Down
          window.LogControls.increase_view_size(-5);
          e.preventDefault();
        }
      } else {
        if (e.keyCode == "38") {
          // Arrow Up
          window.LogControls.move_offset(1);
          e.preventDefault();
        } else if (e.keyCode == "40") {
          // Arrow Down
          window.LogControls.move_offset(-1);
          e.preventDefault();
        } else if (e.keyCode == "33") {
          // Page Up
          window.LogControls.move_offset(5);
          e.preventDefault();
        } else if (e.keyCode == "34") {
          // Page Down
          window.LogControls.move_offset(-5);
          e.preventDefault();
        }
      }
    }

    document.onkeyup = checkKey;
  },
  false
);
