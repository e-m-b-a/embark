// jshint unused:false
// ^ this should only be added AFTER successfull check (disables waring for global functions)

var nxpie = document.getElementById('nxpie').getContext('2d');
var piepie = document.getElementById('piepie').getContext('2d');
var relropie = document.getElementById('relropie').getContext('2d');
var canarypie = document.getElementById('canarypie').getContext('2d');
var strippedpie = document.getElementById('strippedpie').getContext('2d');

var accumulatedCvePie = document.getElementById('accumulatedCvePie').getContext('2d');

var accumulatedArchitecture = document.getElementById('accumulatedArchitecture').getContext('2d');
var accumulatedOs = document.getElementById('accumulatedOs').getContext('2d');
// TODO put system emulation stuff here

var firmwareAnalysed = document.getElementById('firmwareAnalysed');
var totalFiles = document.getElementById('totalFiles');
var totalDirectories = document.getElementById('totalDirectories');
var totalBinaries = document.getElementById('totalBinaries');
var totalCve = document.getElementById('totalCve');
var totalIssues = document.getElementById('totalIssues');



var topBinaryTypes = document.getElementById('topBinaryTypes').getContext('2d');
var topSystemBinsTypes = document.getElementById('topSystemBinsTypes').getContext('2d');




/**
 * Get Random Colors for the Charts .
 * @param {*} num Number of Colors required for the chart
 * @returns Array of colors with RGB values
 */
// TODO: make direct call, no array! simplify
function getRandomColors(num) {
    "use strict";
    try {
            var colors = [];
            for (var i = 0; i < num; i++) {
                var r = Math.round(Math.random() * 255);
                var g = Math.round(Math.random() * 255);
                var b = Math.round(Math.random() * 255);
                colors.push(`rgba(${r}, ${g}, ${b})`);
            }
            return colors;    
    } catch (error) {
        console.log(error.message);
        location.reload();
    }
    
}

/**
* Inits Chart instances from report-data
* @param {*} returnData report-data from emba
*/
function makeCharts(returnData) {
    "use strict";
    if (returnData.total_firmwares !== 0) {
      firmwareAnalysed.textContent = returnData.total_firmwares;
      totalFiles.textContent = returnData.files.sum;
      totalDirectories.textContent = returnData.directories.sum;
      totalBinaries.textContent = returnData.bins_checked.sum;
      totalCve.textContent = returnData.cve_medium.sum + returnData.cve_low.sum + returnData.cve_high.sum;
      totalIssues.textContent = returnData.exploits.sum;
    } else {
      firmwareAnalysed.textContent = "no data";
      totalFiles.textContent = "no data";
      totalDirectories.textContent = "no data";
      totalBinaries.textContent = "no data";
      totalCve.textContent = "no data";
      totalIssues.textContent = "no data";
    }

    let cvePieChart = new Chart(accumulatedCvePie, {
        type: 'pie',
        data: {
            labels: [
                'CVE-High',
                'CVE-Low',
                'CVE-Medium'
            ],
            datasets: [{
                label: 'CVE DATA',
                data: [returnData.cve_high.sum, returnData.cve_low.sum, returnData.cve_medium.sum],
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

    let nxpiechart = new Chart(nxpie, {
        type: 'pie',
        data: {
            labels: [
                'Binaries without NX',
                'Binaries with NX',
            ],
            datasets: [{
                labels: ['binaries with NX', 'binaries without NX'],
                data: [returnData.no_exec.sum, (returnData.bins_checked.sum - returnData.no_exec.sum)],
                backgroundColor: ['#493791', '#291771'],
            }, ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'No eXecute',
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

    let piepiechart = new Chart(piepie, {
        type: 'pie',
        data: {
            labels: [
                'Not PIE binaries',
                'PIE enabled binaries',
            ],
            datasets: [{
                labels: ['binaries with PIE', 'binaries without PIE'],
                data: [returnData.pie.sum, (returnData.bins_checked.sum - returnData.pie.sum)],
                backgroundColor: ['#1b1534', '#000014'],
            }, ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Position Independent (PIE)',
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

    let relropiechart = new Chart(relropie, {
        type: 'pie',
        data: {
            labels: [
                'Binaries without RELRO',
                'Binaries with RELRO',
            ],
            datasets: [{
                labels: ['binaries with RELRO', 'binaries without RELRO'],
                data: [returnData.relro.sum, (returnData.bins_checked.sum - returnData.relro.sum)],
                backgroundColor: ['#7b919d', '#5b717d'],
            }, ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'RELRO',
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

    let canarypiechart = new Chart(canarypie, {
        type: 'pie',
        data: {
            labels: [
                'Binaries without stack canaries',
                'Binaries with stack canaries',
            ],
            datasets: [{
                labels: ['binaries with CANARY', 'binaries without CANARY'],
                data: [returnData.canary.sum, (returnData.bins_checked.sum - returnData.canary.sum)],
                backgroundColor: ['#525d63', '#323d43'],
            }, ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Stack canaries',
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

    let strippedpiechart = new Chart(strippedpie, {
        type: 'pie',
        data: {
            labels: [
                'Stripped binaries',
                'Not stripped binaries',
            ],
            datasets: [{
                labels: ['binaries with Stripped', 'binaries without Stripped'],
                data: [returnData.stripped.sum, (returnData.bins_checked.sum - returnData.stripped.sum)],
                backgroundColor: ['#009999', '#005050'],
            }, ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Debugging information',
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

    var archLabels = Object.keys(returnData.architecture_verified);
    var archCounts = Object.values(returnData.architecture_verified);
    let architectureBarChart = new Chart(accumulatedArchitecture, {
        type: 'bar',
        data: {
            labels: archLabels,
            datasets: [{
                label: 'Architecture Distribution',
                labels: archLabels,
                data: archCounts,
                borderWidth: 1,
                backgroundColor: getRandomColors(archLabels.length)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Architecture Distribution',
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

    var osLabels = Object.keys(returnData.os_verified);
    var osCounts = Object.values(returnData.os_verified);
    let osBarChart = new Chart(accumulatedOs, {
        type: 'bar',
        data: {
            labels: osLabels,
            datasets: [{
                label: 'OS Distribution',
                labels: osLabels,
                data: osCounts,
                borderWidth: 1,
                backgroundColor: getRandomColors(osLabels.length)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'OS Distribution',
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
        },
    });


    var topBinaryLabels = Object.keys(returnData.top_strcpy_bins);
    var topBinaryCounts = Object.values(returnData.top_strcpy_bins);
    let topBinaryBar = new Chart(topBinaryTypes, {
        type: 'bar',
        data: {
            labels: topBinaryLabels,
            datasets: [{
                label: 'Number of STRCPY used',
                labels: topBinaryLabels,
                data: topBinaryCounts,
                borderWidth: 1,
                backgroundColor: getRandomColors(topBinaryLabels.length)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Binaries using legacy C-function strcpy',
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
        },

    });


    var topSystemBinsLabels = Object.keys(returnData.top_system_bins);
    var topSystemBinsCounts = Object.values(returnData.top_system_bins);
    let topSystemBinsBar = new Chart(topSystemBinsTypes, {
        type: 'bar',
        data: {
            labels: topSystemBinsLabels,
            datasets: [{
                label: 'Used in X files',
                labels: topSystemBinsLabels,
                data: topSystemBinsCounts,
                borderWidth: 1,
                backgroundColor: getRandomColors(topSystemBinsLabels.length)
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Binaries using C-function system',
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
        },

    });

}

/**
 * Gets Accumulated data of all firmware scans analysed.
 * @returns Data for the Graphs
 */
function get_accumulated_reports() {
    "use strict";
    try {
        let url = window.location.origin + "/get_accumulated_reports/";
        return $.getJSON(url).then(function (data) {
        console.log(data);
        return data;
        });    
    } catch (error) {
        console.log(error.message);
        location.reload();
    }
    
}

/**
 * Develop Charts from the Analysed data .
 */
 get_accumulated_reports().then(makeCharts);
