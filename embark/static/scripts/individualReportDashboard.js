var accumulatedCvePie = document.getElementById('accumulatedCvePie').getContext('2d');

var nxpie = document.getElementById('nxpie').getContext('2d');
var piepie = document.getElementById('piepie').getContext('2d');
var relropie = document.getElementById('relropie').getContext('2d');
var canarypie = document.getElementById('canarypie').getContext('2d');
var strippedpie = document.getElementById('strippedpie').getContext('2d');

get_individual_report().then(function (returnData) {

    let cvePieChart = new Chart(accumulatedCvePie, {
        type: 'pie',
        data : {
            labels: [
                'CVE-High',
                'CVE-Low',
                'CVE-Medium'
            ],
            datasets: [{
                label: 'CVE DATA',
                data: [returnData.cve_high, returnData.cve_low, returnData.cve_medium],
                backgroundColor: [
                  'rgb(255, 99, 132)',
                  'rgb(54, 162, 235)',
                  'rgb(255, 205, 86)'
                ],
                hoverOffset: 4
              }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                title: {
                    display: false,
                    text: 'CVE Data',
                    fontSize: 25
                },
                legend: {
                    display: false,
                    position: 'right',
                    labels: {
                        fontColor: '#000'
                    }
                },
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        bottom: 0,
                        top: 0
                    }
                },
                tooltips: {
                    enabled: true
                }
        }
    });

    make_chart(relropie, 'Binaries with RELRO', 'Binaries without RELRO',
        '#493791', '#291771', returnData.bins_checked, returnData.relro, 'Binary Protections')
    make_chart(nxpie, 'Binaries with NX','Binaries without NX',
        '#1b1534', '#000014', returnData.bins_checked, returnData.nx, 'Binary Protections')
    make_chart(piepie, 'Binaries with PIE', 'Binaries without PIE',
        '#7b919d', '#5b717d', returnData.bins_checked, returnData.pie, 'Binary Protections')
    make_chart(canarypie, 'Binaries with CANARY', 'Binaries without CANARY',
        '#525d63', '#323d43', returnData.bins_checked, returnData.canary, 'Binary Protections')
    make_chart(strippedpie, 'Binaries with STRIPPED', 'Binaries without STRIPPED',
        '#009999', '#005050', returnData.bins_checked, returnData.stripped, 'Binary Protections')

    let data_to_display = {
        "firmware name": returnData.name,
        "start date": returnData.start_date.replace('T', ' - '),
        "end date": returnData.end_date.replace('T', ' - '),
        "architecture verified": returnData.architecture_verified,
        "vendor": returnData.vendor,
        "version": returnData.version,
        "notes": returnData.notes,
        "files": returnData.files,
        "directories": returnData.directories,
        "bins checked": returnData.bins_checked,
        "exploits": returnData.exploits,
        "entropy_value": returnData.entropy_value,
        "path to logs": returnData.path_to_logs,
        "emba command": "./emba.sh -f /app/embark/uploadedFirmwareImages/active_2/170.pdf -l /app/emba/emba_logs/2  -g -s -z -W -F -t",
    }

    for (const [key, value] of Object.entries(returnData.strcpy_bin)) {
            data_to_display["strcpy bin: " + key] = value
    }

    const table = document.getElementById("detail_body");
    for (const [key, value] of Object.entries(data_to_display)) {
        let row = table.insertRow();
        let date = row.insertCell(0);
        date.innerHTML = key
        let name = row.insertCell(1);
        name.innerHTML = value;
    }
});

function get_individual_report() {
    let report_index = window.location.href.substring(window.location.href.lastIndexOf('/') + 1);
    let url = window.location.origin + "/get_individual_report/" + report_index;

    return $.getJSON(url).then(function(data){
        return data
    })
}

function make_chart(html_chart, label_1, label_2, color_1, color_2, data_cmp, data_strcpy, title) {
        let chart = new Chart(html_chart, {
        type: 'pie',
        data: {
            labels: [label_1, label_2],
            datasets: [
                {
                    labels: [label_1, label_2],
                    data: [data_strcpy, (data_cmp - data_strcpy)],
                    backgroundColor: [color_1, color_2],
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            title: {
                display: false,
                text: title,
                fontSize: 25
            },
            legend: {
                position: 'top',
                labels: {
                    fontColor: '#000'
                }
            },
        }
    });
}