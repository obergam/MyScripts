import csv
import os
import json

os.chdir(r'/Users/oxb/MyScripts/Kount/postmanTools')
with open('Orgs.csv', newline='') as csvfile:
    spamreader = csv.reader(csvfile)
    for row in spamreader:
        data = {"value": row[0],"dateAdded": "2021-12-09T18:42:30-06:00"}
        #dictio = str(data)
        print(json.dumps(data) + ",")