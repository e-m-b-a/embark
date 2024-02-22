
function search(input) {
    var value = input.toLowerCase();
    if (value.startsWith("label=")){
        value = value.slice(6);
        $("#report-table tr").filter(function() {
            $(this).toggle($(this).find(".label").text().toLowerCase().indexOf(value) > -1);
            console.log($(this).find(".label").text().toLowerCase());
            console.log("looking for " + value);
            
        });
    } else{
        $("#report-table tr").filter(function() {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    };
};

function onclick_label(value) {
    var search_bar = $('#search');
    if (search_bar.val().startsWith("label=")){
        search_bar.val(search_bar.val() + value.slice(6));
    } else {
        search_bar.val(search_bar.val() + value);
    };
    search(value);
};
