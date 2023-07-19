#!/usr/bin/env python3
# encoding: utf8
# -*- coding: utf-8 -*-
#
# set lab network 1
#
# Copyright 2016-2021 Yunhui Fu <yhfudev@gmail.com>
#
__author__ = 'Yunhui Fu'
__version__ = 'v0.1.1'
__license__ = 'GPLv3'

import os
import pexpect

## Switch Class
#
#  The class defines the common functions(vitural functions) between various type of switchs/routers
class Switch():
    def __init__(self):
        #add properties etc.
        self._pexp = None
        self._has_hw = False
        self._is_gns3 = True
    def __str__(self):
        return self.__class__.__name__

    ## Check/Set if this device is for GNS3 network simulator
    #  @param self The object pointer.
    #  @param value A boolean value indicate the status.
    def set_is_gns3(self, value):
        self._is_gns3 = value
    def get_is_gns3(self):
        return self._is_gns3
    is_gns3 = property(get_is_gns3, set_is_gns3)

    ## Check/Set the connection to the device
    #  @param self The object pointer.
    #  @param value A pexpect or one like.
    def set_pexp(self, value):
        #if not isinstance(value, pexpect.object.kind):
        #    raise Exception("Error: not a pexpect class!")
        self._pexp = value
    def get_pexp(self):
        return self._pexp
    pexp = property(get_pexp, set_pexp)

    ## Check/Set if the device has hardware switch
    #  @param self The object pointer.
    #  @param value A boolean value indicate the status.
    def set_has_hw_switch(self, value):
        self._has_hw = value
    def get_has_hw_switch(self):
        return self._has_hw
    has_hw_switch = property(get_has_hw_switch, set_has_hw_switch)

    ## save the current config to disk
    #  @param self The object pointer.
    def save_config(self):
        raise NotImplementedError()
        return False

    ## reboot the device
    #  @param self The object pointer.
    def reboot(self, wait_network=True):
        raise NotImplementedError()
        return False

    ## get the device board info
    #  @param self The object pointer.
    def get_board(self):
        #raise NotImplementedError(); return None
        return self.get_model_name()

    ## get the device model name
    #  @param self The object pointer.
    def get_model_name(self):
        raise NotImplementedError()
        return None

    ## get the device FW version
    #  @param self The object pointer.
    def get_version(self):
        raise NotImplementedError()
        return None

    ## reset the device
    #  @param self The object pointer.
    #  @param port_map: port map from external name to internal id/name, such as port_map = {'CPU':0, 'WAN': 1, 'LAN1': 2}; port_map = {'g1': 'g1', 'WAN': 'Gi0/1'}
    def reset_config(self, port_map):
        raise NotImplementedError()
        return False

    ## get the device hostname
    #  @param self The object pointer.
    #  @param hostname The hostname.
    def get_hostname(self):
        raise NotImplementedError()
        return None
    def set_hostname(self, hostname):
        raise NotImplementedError()
        return False
    hostname = property(get_hostname, set_hostname)

    ## get a list of VLAN id
    def get_vlans(self):
        raise NotImplementedError()
        return None

    ## set the root password
    #  @param self The object pointer.
    #  @param root_pw The password.
    def set_root_passwd(self, root_pw):
        raise NotImplementedError()
        return False

    ## set current time to device
    #  @param self The object pointer.
    def set_clock(self):
        raise NotImplementedError()
        return False

    ## get current time of device
    #  @param self The object pointer.
    def get_clock(self):
        raise NotImplementedError()
        return None

    #clock = property(get_clock, set_clock)

    ## set VLANs for the device
    #  @param port_map The port map from external name to internal id/name, such as port_map = {'CPU':0, 'WAN': 1, 'LAN1': 2}; port_map = {'g1': 'g1', 'WAN': 'Gi0/1'}
    #  @param vlan_set A full vlan set, example {5,6,10,20,...,120}
    #  @param vlan_list The vlan id list for each port in ports_list; the values: -1 -- ignore, 0 -- trunk, 1-1024 -- vlan id
    #  @param port_list A list of port
    def set_vlans(self, port_map, port_list, vlan_list, vlan_set, interface_config={}):
        raise NotImplementedError()
        return False


# pexpect clean buffer
def pexpect_clean_buffer(pexp):
    #return # ignore
    buff = None
    try:
        buff = pexp.read_nonblocking(16384, timeout = 1)
        print('clear_buffer(): read_nonblocking: ***{0}***'.format(buff))
    except pexpect.exceptions.TIMEOUT as toe:
        print('clear_buffer(): TIMEOUT: {1}, buff: ***{0}***'.format(buff,str(toe)))

# pexpect clean buffer
def pexpect_clean_buffer2(pexp):
    flushedStuff = ''
    try:
        while not pexp.expect(r'.+', timeout=2):
            flushedStuff = pexp.match.group(0)
    except pexpect.exceptions.TIMEOUT as toe:
        pass

## convert a port_vlan dict to two lists
def port_vlan_to_lists(port_vlan):
    if (len(port_vlan) < 1): return None
    port_list = list(port_vlan.keys()); port_list.sort()
    vlan_list = [port_vlan[i] for i in port_list]
    return [port_list, vlan_list]

def get_timezone():
    import time
    print(f"get timezone={time.tzname}")
    return list(time.tzname)

if __name__ == '__main__':
    import unittest
    class myTest(unittest.TestCase):
        def setUp(self):
            pass
        def tearDown(self):
            pass

        def test_portvlan2lists_corner(self):
            port_vlan = {}
            self.assertEqual(port_vlan_to_lists(port_vlan), None)

        def test_portvlan2lists_single(self):
            port_vlan = { "WAN": 0 }
            self.assertEqual(port_vlan_to_lists(port_vlan), [["WAN"], [0]])

        def test_portvlan2lists_multi(self):
            port_vlan = {
                "WAN": 0,
                "1": 15,
                "2": 16,
                "3": 17,
                "4": 18,
            }
            self.assertEqual(port_vlan_to_lists(port_vlan), [["1", "2", "3", "4", "WAN"], [15, 16, 17, 18, 0]])

        def test_portvlan2lists_array(self):
            port_vlan = {
                "WAN": [20, 0],
                "1": 15,
                "2": 16,
                "3": 17,
                "4": 18,
            }
            self.assertEqual(port_vlan_to_lists(port_vlan), [["1", "2", "3", "4", "WAN"], [15, 16, 17, 18, [20,0]]])

        def test_portvlan2lists_basi(self):
            port_vlan = {
                "WAN": [20, 0],
                "1": 15,
                "2": 16,
                "3": 17,
                "4": 18,
            }
            [port_list, vlan_list] = port_vlan_to_lists(port_vlan)
            self.assertEqual(port_list, ["1", "2", "3", "4", "WAN"])
            self.assertEqual(vlan_list, [15, 16, 17, 18, [20,0]])

        def test_timezone(self):
            import time
            self.assertEqual(time.tzname, get_timezone())

    unittest.main()
