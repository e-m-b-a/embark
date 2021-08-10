var accumulatedCveDoughnut = document.getElementById('accumulatedCveDoughnut').getContext('2d');

var nxpie = document.getElementById('nxpie').getContext('2d');
var piepie = document.getElementById('piepie').getContext('2d');
var relropie = document.getElementById('relropie').getContext('2d');
var canarypie = document.getElementById('canarypie').getContext('2d');
var strippedpie = document.getElementById('strippedpie').getContext('2d');

/**
 * Generates Reports after you complete receiving the data for Individual Fimware
 */
get_individual_report().then(function (returnData) {

    let cvedoughnutChart = new Chart(accumulatedCveDoughnut, {
        type: 'doughnut',
        data: {
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
            plugins: {
                title: {
                    display: true,
                    text: 'CVE Data',
                    position: 'top',
                    color: 666,
                    padding: {
                        top: 15,
                        bottom: 10
                    },
                    font: {
                        size: 24
                    }
                },
                legend: {
                    display: true,
                    position: 'bottom',
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
        }
    });

    make_chart(relropie, 'Binaries with RELRO', 'Binaries without RELRO',
        '#493791', '#291771', returnData.bins_checked, returnData.relro, 'RELRO')
    make_chart(nxpie, 'Binaries with NX', 'Binaries without NX',
        '#1b1534', '#000014', returnData.bins_checked, returnData.nx, 'NX')
    make_chart(piepie, 'Binaries with PIE', 'Binaries without PIE',
        '#7b919d', '#5b717d', returnData.bins_checked, returnData.pie, 'PIE')
    make_chart(canarypie, 'Binaries with CANARY', 'Binaries without CANARY',
        '#525d63', '#323d43', returnData.bins_checked, returnData.canary, 'CANARY')
    make_chart(strippedpie, 'Binaries with Stripped', 'Binaries without Stripped',
        '#009999', '#005050', returnData.bins_checked, returnData.stripped, 'Stripped')

    let data_to_display = {
        "Firmware name": returnData.name,
        "Start date": returnData.start_date.replace('T', ' - '),
        "End date": returnData.end_date.replace('T', ' - '),
        "Architecture detected": returnData.architecture_verified,
        "Vendor": returnData.vendor,
        "Version": returnData.version,
        "Notes": returnData.notes,
        "Files detected": returnData.files,
        "Directories detected": returnData.directories,
        "Binaries checked": returnData.bins_checked,
        "Exploits identified": returnData.exploits,
        "Entropy value": returnData.entropy_value,
        "Path to logs": returnData.path_to_logs,
        "EMBA command used": "TODO",
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

/**
 * Gets data to generate Reports for Individual Firmware
 * @returns data of the Nalysed Individual firmware
 */
function get_individual_report() {
    let report_index = window.location.href.substring(window.location.href.lastIndexOf('/') + 1);
    let url = window.location.origin + "/get_individual_report/" + report_index;

    return $.getJSON(url).then(function (data) {
        return data
    })
}

/**
 * Develops Chart
 * @param {*} html_chart Type of Chart
 * @param {*} label_1 Labels
 * @param {*} label_2 Labels
 * @param {*} color_1 Colors
 * @param {*} color_2 Colors
 * @param {*} data_cmp Data to be plotted
 * @param {*} data_strcpy
 * @param {*} title Title of The chart
 */
function make_chart(html_chart, label_1, label_2, color_1, color_2, data_cmp, data_strcpy, title) {
    let chart = new Chart(html_chart, {
        type: 'pie',
        data: {
            labels: [label_1, label_2],
            datasets: [{
                labels: [label_1, label_2],
                data: [data_strcpy, (data_cmp - data_strcpy)],
                backgroundColor: [color_1, color_2],
            }, ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    position: 'top',
                    color: 666,
                    padding: {
                        top: 15,
                        bottom: 10
                    },
                    font: {
                        size: 24
                    }
                },
                legend: {
                    display: true,
                    position: 'bottom',
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

        }
    });
}
