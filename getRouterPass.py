#!/usr/bin/env python3


# These three lines should be copied verbatim.  Since your test lives in its own directory, you need to
# add the parent directory to the search path before the import.
import sys
import argparse
sys.path.append('..')
import Router



# To run a test at your desk, you will need to have a "__main__" body for your test.  This code will not be executed by
# the test framework, and you need to perform some of the tasks carried out by the test framework.
if __name__ == '__main__':

    ip = "192.168.17.1"

    help_handler = argparse.ArgumentDefaultsHelpFormatter
    arg_handler = argparse.ArgumentParser(
        description='Get password form router',
        conflict_handler='resolve', formatter_class=help_handler)
    arg_handler.add_argument('-ip', '--ip', dest='ip',
                             help='Router ip address')

    args = vars(arg_handler.parse_args())

    if args['ip']:
        ip = args['ip']

    router =  Router.Router(ip)
    password = router.getDefaultAdminPass()
    mac      = router.getMACViaARP()
    mac2     = router.getMACViaPLT()

    print("Password: {}".format(password))
    print("MAC_ARP: {} ".format(mac))
    print("MAC_PLT: {} ".format(mac2))

    macString = mac.replace(':', '')
    print("Last 8 of mac : %s" % (macString[-8:]))





