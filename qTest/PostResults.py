import requests

qTestTriggerURL = "https://pulse-7.qtestnet.com/webhook/b0e5d8e7-4a75-47fc-a392-1e2580585967"
qtest_projectID = 89593
qtest_testcycle = 3525308


def myPoster(data):
	sendSuccessful = False
	try:
		response = requests.put(qTestTriggerURL, json=data)
		sendSuccessful = True
	except Exception as e:
		print('requests.post had an exception: {}'.format(e))

	if sendSuccessful == True:
		print('qTest reporting succeeded')
		pass
	else:
		print('qTest reporting failed')


filepath = ('SampleACS.xml')
data = {}

with open(filepath, 'r') as file:
	resultsXml = file.read().replace('"', '\"')

data['projectId'] = qtest_projectID
data['testCycle'] = qtest_testcycle
data['result'] = resultsXml

myPoster(data)

