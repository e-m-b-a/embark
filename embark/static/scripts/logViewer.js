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

    window.file_view = {
      offset: 0,
      limit: 50,
      content: "",
    };

    var logArea = document.getElementById("logArea");

    function onError(evt) {
      console.log("error", evt);
    }

    var socket = undefined;

    import('/static/external/scripts/ansi_up.js').then(({ AnsiUp }) => {
      socket = new WebSocket(
        wsStart + location.hostname + wsPort + "/ws/logs/" + analysis_id
      );

      function onMessage(evt) {
        var message = JSON.parse(evt.data);

        if (message.file_view) {
          var fileContent = Base64.decode(message.file_view.content) // We cannot use atob because of unicode (see https://stackoverflow.com/questions/30106476/using-javascripts-atob-to-decode-base64-doesnt-properly-decode-utf-8-strings)
          fileContent = fileContent + "\u00a0"; // The nbsp is required in order to preserve trailing newlines

          var ansi_up = new AnsiUp();
          var coloredFileContent = ansi_up.ansi_to_html(fileContent);
          logArea.innerHTML = coloredFileContent;
          file_view = message.file_view;
        }
      }

      socket.onmessage = function (evt) {
        onMessage(evt);
      };

      socket.onerror = function (evt) {
        onError(evt);
      };
    });

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
