import json, argparse, requests, sys

parser = argparse.ArgumentParser(description='usage: python qtest_xml_convert_and_report.py --f /Users/tester/results.xml --p 5678 --t 1234 -u https://pulse-7.qtestnet.com/webhook/b0e5d8e7-4a75-47fc-a392-1e2580585967')
parser.add_argument("--f", help="junit xml file path")
parser.add_argument("--p", help="qTest project ID")
parser.add_argument("--t", help="qTest test cycle")
parser.add_argument("--u", help="qTest trigger URL")

args = parser.parse_args()

with open(args.f, 'r') as file:
    resultsXml = file.read().replace('"', '\"')

data = {}
data['projectId'] = args.p
data['testCycle'] = args.t
data['result'] = resultsXml

print(data)

# r = requests.post(args.u, json=data)
# r.raise_for_status()
