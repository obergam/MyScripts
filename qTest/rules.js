const request = require('request');
const { Webhooks } = require('@qasymphony/pulse-sdk');
const ScenarioSdk = require('@qasymphony/scenario-sdk');

const Features = {
    getIssueLinkByFeatureName(qtestToken, scenarioProjectId, name) {
        return new ScenarioSdk.Features({ qtestToken, scenarioProjectId }).getFeatures(`"${name}"`);
    }
};

exports.handler = function ({ event: body, constants, triggers }, context, callback) {
    function emitEvent(name, payload) {
        let t = triggers.find(t => t.name === name);
        return t && new Webhooks().invoke(t, payload);
    }

    // Specific to pulse actions
    //"name": "UpdateQTestAndScenarioWithFormattedResults.js"
    var payload = body;

    var testLogs = payload.logs;
    var cycleId = payload.testCycle;
    var projectId = payload.projectId;

    var scenarioCount = 0;
    var scenarioList = "";

    var standardHeaders = {
        'Content-Type': 'application/json',
        'Authorization': `bearer ${constants.QTEST_TOKEN}`
    }

    var createLogsAndTCs = function () {
        var opts = {
            url: "http://" + constants.ManagerURL + "/api/v3/projects/" + projectId + "/auto-test-logs?type=automation",
            json: true,
            headers: standardHeaders,
            body: {
                test_cycle: cycleId,
                test_logs: testLogs
            }
        };

        return request.post(opts, function (err, response, resbody) {

            if (err) {
                Promise.reject(err);
            }
            else {
                console.log('response from qTest Manager:', JSON.stringify(response))
                //emitEvent('SlackEvent', { AutomationLogUploaded: resbody });

                if (response.body.type == "AUTOMATION_TEST_LOG") {
                    Promise.resolve("Uploaded results successfully");
                }
                else {
                    //emitEvent('SlackEvent', { Error: "Wrong type" });
                    Promise.reject("Unable to upload test results");
                }
            }
        });
    };

    createLogsAndTCs()
        .on('response', function () {
            console.log("About to call Link Requirements Rule")
            //emitEvent('LinkScenarioRequirements', payload);
            //linkReq();
        })
        .on('error', function (err) {
            //emitEvent('SlackEvent', { CaughtError: err });
        })
}

//

const { Webhooks } = require('@qasymphony/pulse-sdk');

exports.handler = function ({ event: body, constants, triggers }, context, callback) {
    function emitEvent(name, payload) {
        let t = triggers.find(t => t.name === name);
        return t && new Webhooks().invoke(t, payload);
    }

    var payload = body;
    var testResults = payload.result.replace(/\<testsuites>|\<\/testsuites>/g, '');
    var projectId = payload.projectId;
    var cycleId = payload.testCycle;

    xml2js = require('xml2js');

    var testLogs = [];
    function FormatLogs(tr) {

        var testResults = JSON.parse(tr);
        testResults.testsuite.testcase.forEach(function (tc) {
            var tcResult = tc["$"];
            var tcName = "";

            // Format the name
            var note = "";
            if (!tcResult.name)
                tcName = "Unnamed";
            else
                tcName = tcResult.name;//.substring(0, tcResult.name.indexOf('['));

            //note = tcResult.name;

            TCStatus = "PASS";

            if (tc.failure) {
                TCStatus = "FAIL";
                if (note)
                    note = "\n" + JSON.stringify(tc.failure);
                else
                    note = JSON.stringify(tc.failure);
            }

            // The automation content is what we're going to use to run this later so it's important to get that format for Python pytest
            //$file :: $classname (after the last .) :: $name (before the [)
            var tcShortClassName = tcResult.classname.substring(tcResult.classname.lastIndexOf('.') + 1)
            var auto = tcResult.file + "::" + tcShortClassName + "::" + tcName;

            var reportingLog = {
                exe_start_date: new Date(), // TODO this could use the time to complete to be more precise
                exe_end_date: new Date(),
                module_names: [
                    'JUnitTests'
                ],
                name: tcName,
                automation_content: auto,
                note: note
            };

            // There are no steps here, so we'll add one step entry
            var testStepLogs = [{
                order: 0,
                description: tcName,
                expected_result: tcName,
                status: TCStatus
            }];

            reportingLog.description = "Test case imported from Python Test"
            reportingLog.status = TCStatus;
            reportingLog.test_step_logs = testStepLogs;
            testLogs.push(reportingLog);
        });

        var formattedResults = {
            "projectId": projectId,
            "testCycle": cycleId,
            "logs": testLogs
        };

        return formattedResults;
    }

    var parser = new xml2js.Parser();

    // Pulse Version
    parser.parseString(testResults, function (err, result) {
        var formattedResults = FormatLogs(JSON.stringify(result));
        emitEvent('pytest-already-formatted', formattedResults);
    });
}


