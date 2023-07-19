#!/usr/bin/env python3
# encoding: utf8
# -*- coding: utf-8 -*-
#
# parse various clock time strings
#
# Copyright 2016-2021 Yunhui Fu <yhfudev@gmail.com>
#
__author__ = 'Yunhui Fu'
__version__ = 'v0.1.1'
__license__ = 'GPLv3'

import os
import sys
import time
import re
import ipaddress

if sys.version_info[0] >= 3:
    unicode = str

import logging
L = logging.getLogger('switch')

def get_network_addr(network_string):
    ipnet = None
    try:
        #L.debug("process network: " + str(network_string))
        ipnet = ipaddress.ip_network(unicode(network_string))
    except:
        try:
            #L.warn("try process address again: " + str(network_string))
            ipnet = ipaddress.ip_address(unicode(network_string))
        except Exception as inst:
            #L.error("Unable to cal ip address: "  + str(network_string))
            #L.error("inst: "  + str(inst))
            return None

    if ipnet.num_addresses <= 2:
        L.error("the network is too small.")
        return None
    """
    L.debug("network " + str(network_string) + ", num_addresses=" + str(ipnet.num_addresses) + ", first=" + str(ipnet[0]) + ", last=" + str(ipnet[ipnet.num_addresses-1]))
    L.debug("is_reserved: " + ("yes" if ipnet.is_reserved else "no"));
    L.debug("broadcast: " + str(ipnet.broadcast_address));
    L.debug("hostmask: " + str(ipnet.hostmask));
    L.debug("netmask: " + str(ipnet.netmask));
    L.debug("prefixlen: " + str(ipnet.prefixlen));
    L.debug("num_addresses: " + str(ipnet.num_addresses));
    lst = list(ipnet.hosts())
    L.debug("first host: " + str(lst[0]));
    L.debug("last host: " + str(lst[len(lst)-1]));
    """

    return ipnet

def interfaces_has_subnet_ips(interface_config):
    # detect if the interface has sub-network IPs
    has_subnet_ips = False
    for i in interface_config:
        ipnet = get_network_addr(interface_config[i][1])
        if not (ipnet == None):
            has_subnet_ips = True
    L.debug("return has_subnet_ips={}".format(has_subnet_ips))
    return has_subnet_ips

################################################################################
if __name__ == '__main__':
    import mylog
    L = mylog.setup_custom_logger('switch')
    L.setLevel(logging.DEBUG)

    import unittest
    class myTest(unittest.TestCase):

        def test_get_network_addr(self):
            inet = get_network_addr("192.168.1.0/24")
            self.assertEqual("255.255.255.0", str(inet.netmask))
            self.assertEqual("192.168.1.255", str(inet.broadcast_address))
            inet = get_network_addr("")
            self.assertEqual(None, inet)

        def test_get_network_addr2(self):
            #inet = get_network_addr("10.1.1.000/29")
            inet = get_network_addr("10.1.1.0/29")
            self.assertTrue(inet)
            self.assertEqual("255.255.255.248", str(inet.netmask))
            self.assertEqual("10.1.1.7", str(inet.broadcast_address))

        def test_get_network_addr3(self):
            inet = get_network_addr("10.1.3.0/24")
            self.assertTrue(inet)
            self.assertEqual("255.255.255.0", str(inet.netmask))
            self.assertEqual("10.1.3.255", str(inet.broadcast_address))

        def test_interfaces_has_subnet_ips(self):
            interface_config_1 = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "10.1.1.0/29", "", "", []],
            }
            self.assertEqual(True, interfaces_has_subnet_ips(interface_config_1))
            interface_config_2 = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "", "", "", []],
            }
            self.assertEqual(False, interfaces_has_subnet_ips(interface_config_2))

    unittest.main()
