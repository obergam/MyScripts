#!/usr/bin/env python3

#
# By default the one button upgrade on the router creates this URL in its config:
#   Router fw: http://www.cradlepoint.com/files/uploads/<router model>/firmware-<model>.json  
#          ex: http://www.cradlepoint.com/files/uploads/MBR1400v2/firmware-mbr1400v2.json
#   
# Modem fw update takes the URL at this location and modifies it for its query to look like this:   
#   Modem fw: http://www.cradlepoint.com/files/uploads/MODEM/firmware-<mfg-model>.json
#         ex: http://www.cradlepoint.com/files/uploads/MODEM/firmware-boby-l100.json
#         
# The base URL can be modified from the router's cli by changing /config/system/admin/upgrade_url as follows:
#     set upgrade_url to something like this: "http://75.160.178.212:8000/MBR1400v2/firmware-mbr1400v2.json"
#     Example: this "http://www.cradlepoint.com/files/uploads/MBR1400v2/firmware-mbr1400v2.json"
#              becomes "http://75.160.178.212:8000/MBR1400v2/firmware-mbr1400v2.json"
#              set upgrade_url "http://192.168.50.112:8000/MBR1400v2/firmware-mbr1400v2.json"
#     Note: Change the ip address to reflect the IP address of the PC this server is running on.
#          
# Modify the .json file to change the address as well.The packager script creates two json files, one for one button and another for USB. Take the one that 
# is something like firmware-xxx.json
# 
# Set up a port forwarding rule on the router to forward port 8000 to the PC running this server.
# 
# For modem fw upgrade, the router will look in the same root directory as configured above but for the file firmware-MODEM.json
import http.server
import socketserver

PORT = 8000


class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_my_headers()

        super().end_headers()

    def send_my_headers(self):
        self.send_header("Content-Type", "text/plain; charset=UTF-8")

Handler = MyHTTPRequestHandler

httpd = socketserver.TCPServer(("", PORT), Handler)

print("serving at port", PORT)
httpd.serve_forever()


