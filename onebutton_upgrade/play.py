import subprocess
import json
import sys

def get_val(password, pth):
    get_req = 'curl -s  -u admin:{} --connect-timeout 20 -X GET http://10.31.17.1/api/{}'.format(password, pth)
    proc = subprocess.Popen(get_req.split(),stdout=subprocess.PIPE)
    resp = proc.communicate()[0]
    #communicate returns a bytes array. Need to convert to string so we can do a regular expression match
    """try:
        resp = resp.decode("utf-8")
    except Exception as e:
        self.log("get_val, no decode")
        return None, -1
    try:
        json_data = json.loads(resp)
        if json_data == None:
            self.log("get_val, no json")
            return None, -1
        if json_data['success'] == False:
            self.log("get_val, returned false")
            return None, 0
        else:
            self.log("get_val, returned true")
            print(json_data['data'])
            return json_data['data'],1
    except:
        self.log("get_val, exception")
        return None,-1"""


if __name__ == "__main__":
    admin_password = '442cfedd'
    pth = 'config/system/firewall/remote_admin'
    tester = get_val(admin_password, pth)
    print(tester)
    if tester == True:
        print("It's True!")
    else:
        print("It's not true!")
