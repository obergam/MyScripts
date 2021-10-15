import json
import os

os.chdir(r'/Users/oxb/MyScripts/incomm')
with open('pol.json') as json_file:
    data = json.load(json_file)

# IF "factId": "ae80e14e-2e57-4725-aa0c-864a7fe8edc7", "comparator": "eq",
#policyId profiles guidance tags IF 
key = "profiles"
key2 = "tags"

for policy in data['policies']:
    if key in policy.keys():
        if key2 in policy.keys():
            if policy["conditions"][0]["factId"] == "ae80e14e-2e57-4725-aa0c-864a7fe8edc7":
                if policy["conditions"][0]["comparator"] == "eq":
                    if policy["profiles"][0] != "61010f91-1595-45be-894c-e68bb3423989":
                        if policy["tags"][0] != "5126b3d9-e7a5-4ab8-a5a7-ca40272a5a9d":
                            if policy["guidance"] == "Challenge":
                                value = policy["conditions"][0]["value"]
                                creationDate = policy["creationDate"]
                                data = {"value": value,"dateAdded": creationDate}
                                print(json.dumps(data) + ",")




# with open('new.json', 'w') as f:
#     json.dump(data, f)