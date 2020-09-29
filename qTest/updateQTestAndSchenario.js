const request = require('request');
const { Webhooks } = require('@qasymphony/pulse-sdk');
const ScenarioSdk = require('@qasymphony/scenario-sdk');
const Features = {
    getIssueLinkByFeatureName(qtestToken, scenarioProjectId, name) {
            return new ScenarioSdk.Features({ qtestToken, scenarioProjectId }).getFeatures(`\"${name}\"`);
                }
                };
                exports.handler = function ({ event: body, constants, triggers }, context, callback) {
                    function emitEvent(name, payload) {
                            let t = triggers.find(t => t.name === name);
                            return t && new Webhooks().invoke(t, payload);
                                }

    }
}
"code": "const { Webhooks } = require('@qasymphony/pulse-sdk');

exports.handler = function ({ event: body, constants, triggers }, context, callback) {
    function emitEvent(name, payload) {
            let t = triggers.find(t => t.name === name);
                    return t && new Webhooks().invoke(t, payload);
                        }

                            var payload = body;
                                var testResults = payload.result.replace(/\\<testsuites>|\\<\\/testsuites>/g, '');
                                    var projectId = payload.projectId;
                                        var cycleId = payload.testCycle;

                                            xml2js = require('xml2js');

                                                var testLogs = [];
                                                    function FormatLogs(tr) {

                                                            var testResults = JSON.parse(tr);
                                                                    testResults.testsuite.testcase.forEach(function (tc) {
                                                                                var tcResult = tc[\"$\"];
                                                                                            var tcName = \"\";

                                                                                                        // Format the name
                                                                                                                    var note = \"\";
                                                                                                                                if (!tcResult.name)
                                                                                                                                                tcName = \"Unnamed\";
                                                                                                                                                            else
                                                                                                                                                                            tcName = tcResult.name;
                                                                                                                                                                            //.substring(0, tcResult.name.indexOf('['));

                                                                                                                                                                                        //note = tcResult.name;

                                                                                                                                                                                                    TCStatus = \"PASS\";

                                                                                                                                                                                                                if (tc.failure) {
                                                                                                                                                                                                                                TCStatus = \"FAIL\";
                                                                                                                                                                                                                                                if (note)
                                                                                                                                                                                                                                                                    note = \"\
                                                                                                                                                                                                                                                                    \" + JSON.stringify(tc.failure);
                                                                                                                                                                                                                                                                                    else
                                                                                                                                                                                                                                                                                                        note = JSON.stringify(tc.failure);\n            }\n\n            // The automation content is what we're going to use to run this later so it's important to get that format for Python pytest\n            //$file :: $classname (after the last .) :: $name (before the [)\n            var tcShortClassName = tcResult.classname.substring(tcResult.classname.lastIndexOf('.') + 1)\n            var auto = tcResult.file + \"::\" + tcShortClassName + \"::\" + tcName;\n\n            var reportingLog = {\n                exe_start_date: new Date(), // TODO this could use the time to complete to be more precise\n                exe_end_date: new Date(),\n                module_names: [\n                    'JUnitTests'\n                ],\n                name: tcName,\n                automation_content: auto,\n                note: note\n            };\n\n            // There are no steps here, so we'll add one step entry\n            var testStepLogs = [{\n                order: 0,\n                description: tcName,\n                expected_result: tcName,\n                status: TCStatus\n            }];\n\n            reportingLog.description = \"Test case imported from Python Test\"\n            reportingLog.status = TCStatus;\n            reportingLog.test_step_logs = testStepLogs;\n            testLogs.push(reportingLog);\n        });\n\n        var formattedResults = {\n            \"projectId\": projectId,\n            \"testCycle\": cycleId,\n            \"logs\": testLogs\n        };\n\n        return formattedResults;\n    }\n\n    var parser = new xml2js.Parser();\n\n    // Pulse Version\n    parser.parseString(testResults, function (err, result) {\n        var formattedResults = FormatLogs(JSON.stringify(result));\n        emitEvent('pytest-already-formatted', formattedResults);\n    });\n}\n"
                                                                                                                                                                                                                }
                                                                    }
                                                    }
    }
}
    }