**How to check what type of firmware my device will accept?**
* use this command:
```
[console@IBR900-a03: /]$ cat /status/fw_info/sign_cert_types
"ROOTCA DEBUG"
```


**How to make my device accept debug and release signatures?**
* Use the script tools/signing/convert.py provided by the coconut repository.

**IMPORTANT:** _techsupport license file for the router must be available before the script is run._
* Default license file location is ../tools/signing/techsupport.lic

```
% python tools/signing/convert.py -c <cproot password>
- Opening SSH connection to router at 192.168.0.1...
- Starting HTTP file server on port 8000...
- Reading 'techsupport.lic' from '/home/juan/Repositories/coconut/techsupport.lic'
- Opening SSH connection to router at 192.168.0.1...
- Transfering altrootca.crt to /var/tmp/altcerts/altrootca.crt
- Transfering sig to /var/tmp/altcerts/sig
192.168.0.1 - - [05/Oct/2018 10:55:40] "GET /altrootca.crt HTTP/1.1" 200 -
- Transfering chain to /var/tmp/altcerts/chain
192.168.0.1 - - [05/Oct/2018 10:55:41] "GET /sig HTTP/1.1" 200 -
192.168.0.1 - - [05/Oct/2018 10:55:42] "GET /chain HTTP/1.1" 200 -
- File transfer complete
- Opening SSH connection to router at 192.168.0.1...
Available certificates on device: "DEBUG, RELEASE"
```

Now your device will accept upgrades signed with release and debug
certificates. Apply the firmware of your choice before rebooting the router.

When you reboot your device, you are left with only the one certificate
belonging to the installed firmware.

**change script defaults using optional parameters:**
```
usage: convert.py [-h] [-i HOSTIP] [-p HOSTPORT] [-r ROUTERIP] [-s SSHPORT] [-l LICENSEFILE] -a ADMINPWD
```
Arg | Description | Default
--- | ----------- | -------
 -a | ADMINPWD    | none
 -h | show help message and exit | --
 -i | HOSTIP      | 192.168.0.5
 -p | HOSTPORT    | 8000
 -r | ROUTERIP    | 192.168.0.1
 -s | SSHPORT     | 22
 -l | LICENSEFILE | ../tools/signing/techsupport.lic

_2020-01-15_
Possibly more current instructions may be found on the
[wiki](https://cradlepoint.atlassian.net/wiki/spaces/FW/pages/415006916/Signed+firmware.+How+to+convert)
