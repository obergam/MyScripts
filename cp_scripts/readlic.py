#!/usr/bin/python3

import json
import sys

with open(sys.argv[1], 'r') as f:
    rawstr = f.read()

# jsonstr is all you need to use in a request
jsonstr = rawstr[rawstr.find('{'):]

# if you want to process it as json
data = json.loads(jsonstr)

print("\nPython dict FYI:\n {}".format(data))
print("\nJSON to copy/paste:\n {}".format(json.dumps(data)))
