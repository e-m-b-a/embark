
/** Error alert - Displays Alert message if something is failed 
 * @param {*} message - message to be shown to user
 */
 function errorAlert(message) {
    $.confirm({
       title:  'Error!',
       content: message,
       type: 'red',
       typeAnimated: true,
       buttons: {
           close: function () {
           }
       }
   });
     
  }
 
  /**
   * Success Alert - Display success message to user
   * @param {*} message - Display message  to be shown to user
   */
  function successAlert(message) {
    $.confirm({
       title:  'Success!',
       content: message,
       type: 'green',
       typeAnimated: true,
       buttons: {
           close: function () {
           }
       }
   });
  }
 
  /**
   * For any input which is required by user .
   * @param {*} message Display message to user 
   */
  function promptAlert(message) {
    $.confirm({
      title: 'Prompt!',
      content: '' +
      '<form action="" class="formName">' +
      '<div class="form-group">' +
      '<label>'+ message +'</label>' +
      '<input type="text" placeholder="Your name" class="name form-control" required />' +
      '</div>' +
      '</form>',
      buttons: {
          formSubmit: {
              text: 'Submit',
              btnClass: 'btn-blue',
              action: function () {
                  var name = this.$content.find('.name').val();
                  if(!name){
                      $.alert('Please fill the text ');
                      return false;
                  }
                  $.alert('You entered ' + name);
              }
          },
          cancel: function () {
          },
      },
      onContentReady: function () {
          var jc = this;
          this.$content.find('form').on('submit', function (e) {
              e.preventDefault();
              jc.$$formSubmit.trigger('click');
         });
      }
  });
  }
  