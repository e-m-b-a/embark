check_login();

var loadChart = document.getElementById('loadChart').getContext('2d');

get_load().then(function (returndata) {

    let lineChart = new Chart(loadChart, {
        type: 'line', // bar, horizontalBar, pie, line, doughnut, radar, polarArea
        data: {
            labels: returndata.time,
            datasets: [{
                    label: 'CPU',
                    data: returndata.cpu,
                    borderColor: 'rgba(255, 127, 64, 1)',
                    backgroundColor: 'rgba(255, 127, 64, 0.2)',
                    borderWidth: 2,
                    hoverBorderWidth: 8,
                    hoverBorderColor: 'rgba(255, 127, 64, 1)',
                    fill: true,
                    cubicInterpolationMode: 'monotone'
                },
                {
                    label: 'MEM',
                    data: returndata.mem,
                    borderColor: 'rgba(64,127,255,1)',
                    backgroundColor: 'rgba(64,127,255, 0.2)',
                    borderWidth: 2,
                    hoverBorderWidth: 8,
                    hoverBorderColor: 'rgba(64,127,255,1)',
                    fill: true,
                    cubicInterpolationMode: 'monotone'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            title: {
                display: false,
                text: 'CPU / Memory utilization percentage',
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
            scales: {
                x: {
                    ticks: {
                        display: true,
                        autoSkip: false,
                        maxRotation: 0,
                        minRotation: 0,
                        callback: function(val, index) {
                            // Hide the label of every 2nd dataset
                            return index % 20 === 0 ? this.getLabelForValue(val).split('T')[1].split('.')[0] : '';
                          },
                    }
                },
                y: {
                    min: 0,
                    max: 100,
                    stepSize: 5
                }
            },
            tooltips: {
                enabled: true
            }
        }
    });
});

function get_load() {
    let url = window.location.origin + "/get_load/";

    return $.getJSON(url).then(function (data) {

        return {
            time: data.timestamp,
            cpu: data.cpu_percentage,
            mem: data.memory_percentage
        }
    })
}

function check_login() {
    let url = window.location.origin + "/check_login/";

    return $.getJSON(url);
}