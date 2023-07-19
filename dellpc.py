#!/usr/bin/env python3
# encoding: utf8
# -*- coding: utf-8 -*-
#
# The config functions for Dell PowerConnect 5324
#
# Copyright 2016-2021 Yunhui Fu <yhfudev@gmail.com>
#
__author__ = 'Yunhui Fu'
__version__ = 'v0.1.1'
__license__ = 'GPLv3'

import os
import sys
import random
import logging as L
import ipaddress
import time

import re
import pexpect

from switchdevice import Switch
from parseclock import parse_clock_dellpc

try:
    FileNotFoundError # python 3
except NameError:
    FileNotFoundError = IOError # python 2

if sys.version_info[0] >= 3:
    unicode = str

PROGRAM_PREFIX = os.path.basename(__file__).split('.')[0]

import logging
L = logging.getLogger('switch')

################################################################################
def parse_model_line(str_model):
    search1 = re.search('\n.*System Description(.*)\s', str_model)
    L.debug("search = {0}".format(search1))
    L.debug("search[0]= {0}".format(search1.group(0)))
    return re.split(r':', search1.group(0))[1].strip()

def parse_version_line(str_version):
    L.debug("version search=" + str(re.search('SW version(.*)\s', str_version).group(0)))
    return re.split(r'[\s\t\r\n]+', re.search('SW version(.*)\s', str_version).group(0))[2].strip()

# parse the output of command 'show int status'
def parse_ports(str_output):
    vlan_list = []
    lines = re.split(r'\n', str_output)
    flg_found = False
    for i in range(2, len(lines)):
        ln = lines[i].strip()
        if ln == '':
            continue
        if not flg_found:
            if re.search('---- ', ln):
                flg_found = True
            continue
        if re.search('---- ', ln):
            # its another part
            break
        lst = re.split(r'[\s\t\n]+', lines[i])
        L.debug("split ports line: {0}".format(lst))
        if not len(lst) == 10:
            L.info("not a 9 items: {0}".format(lst))
            break
        vlan_list.append(lst[0])
    L.debug("parse_ports return list = {0}".format(vlan_list))
    return vlan_list

# parse the output of command 'sh vlan-switch brief'
def parse_vlans(str_output):
    ret_vlan = []
    vlan_list = []
    L.debug("start parsing vlan block: '{0}'".format(str_output))
    lines = re.split(r'\n', str_output)
    flg_found = False
    for i in range(0, len(lines)):
        ln = lines[i].strip()
        L.debug("parse vlan line: '{0}'".format(ln))
        if ln == '':
            L.debug("parse vlan line NULL")
            continue
        if not flg_found:
            L.debug("not start parsing")
            if re.search('---- ', ln):
                flg_found = True
                L.debug("start parsing for next line")
            continue
        if re.search('---- ', ln):
            # its another part
            L.debug("end of ----")
            break
        lst = re.split(r'[\s\t\n]+', ln)
        L.debug("split ports line: {0}".format(lst))
        if len(lst) < 4:
            L.warning("not a item: {0}".format(lst))
            break
        vlan_list.append(lst[0])
    L.debug("parse vlan list = {0}".format(vlan_list))
    vlan_list = [int(i) for i in vlan_list]
    return vlan_list

def parse_host_name(str_output):
    search1 = re.search('\n.*System Name(.*)\s', str_output)
    L.debug("search = {0}".format(search1))
    L.debug("search[0]= {0}".format(search1.group(0)))
    return re.split(r':', search1.group(0))[1].strip()

################################################################################
class DellSwitch(Switch):
    def __init__(self):
        super().__init__()

    def _enter_enable(self):
        L.debug("enter to console")
        self.pexp.sendline("\r\nend\r\n")

        #self.pexp.sendcontrol('c')
        while True:
            L.debug("enter to active prompt ...")
            time.sleep(1)
            self.pexp.sendline("\r\n\r\n")
            #self.pexp.sendline('\r\nsh run | i ostname\r\n')
            responses = ["Press RETURN to get started.", ">", "#", pexpect.EOF, pexpect.TIMEOUT]
            ret = self.pexp.expect(responses, timeout=3)
            #if ret < 3:
            #    ln_before = self.pexp.before.decode('UTF-8')
            #    ln_after = self.pexp.after.decode('UTF-8')
            #    L.debug("enter_enable ln_before=" + str(ln_before))
            #    L.debug("enter_enable ln_after=" + str(ln_after))
            #    L.debug("got response: {0}".format(responses[ret]))
            if ret == 0:
                L.debug("i need a RETURN!!")
                continue
            elif ret == 1:
                L.debug("enter to enable ...")
                self.pexp.sendline("enable\r\n")
            elif ret == 2:
                L.debug("got a '#'")
                break
            else:
                L.debug("got eof/timeout")
                pass

        L.debug("done, it's in 'enable' state")

    def _quit_enable(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline('end\r\n')
        self.pexp.sendline("exit\r\n")
        self.pexp.sendline()

    def show_info(self):
        self.pexp.sendline('show interfaces status\r\n')
        self.pexp.sendline('show vlan\r\n')
        self.pexp.sendline('show ip interface vlan 1\r\n')
        self.pexp.sendline('show system\r\n')
        self.pexp.sendline('show clock\r\n')

    # save the current config to disk
    def save_config(self):
        self._enter_enable()
        self.pexp.sendline("copy running-config startup-config\r\n")
        self.pexp.expect("The copy operation was completed successfully")

    # reboot system
    def reboot(self, wait_network=True):
        hostname = self.get_hostname()
        self._enter_enable()
        L.info("reboot ...")
        while True:
            L.debug("send 'reload' ...")
            self.pexp.sendline("reload")
            ret = self.pexp.expect(["\(Y/N\)","{0}#".format(hostname)])
            L.debug("get respose: {0}".format(ret))
            if ret == 0:
                L.debug("send reboot 'Y' ans ...")
                self.pexp.sendline("Y\r\n")
                ret = self.pexp.expect(["Shutting down","{0}#".format(hostname)])
                if ret == 0:
                    break
            time.sleep(1)

        ret = self.pexp.expect(["press RETURN or Esc."])

        L.info("reboot DONE")

    def get_model_name(self):
        self._enter_enable()
        self.pexp.sendline('show system\r\n')
        self.pexp.expect('Main Power Supply Status')
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("model ln_before=" + str(ln_before))
        L.debug("model ln_after=" + str(ln_after))
        return parse_model_line(ln_before)

    def get_version(self):
        self._enter_enable()
        self.pexp.sendline('sh ver\r\n')
        #time.sleep(3)
        self.pexp.expect('Boot version')
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("version ln_before=" + str(ln_before))
        L.debug("version ln_after=" + str(ln_after))
        return parse_version_line(ln_before)

    def get_version_num(self):
        ver = self.get_version()
        return float(re.split(r'\.', ver)[0].strip())

    # get a list of ports
    def get_ports(self):
        self._enter_enable()
        self.pexp.sendline("show int status\r\n")
        self.pexp.expect("Ch       Type    Duplex  Speed  Neg      control  State")
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("vlan-switch ln_before=" + str(ln_before))
        L.debug("vlan-switch ln_after=" + str(ln_after))
        return parse_vlans(ln_before)

    # get a list of vlan
    def get_vlans(self):
        self._enter_enable()
        self.pexp.sendline("show vlan\r\n")
        time.sleep(1)
        self.pexp.expect("Authorization")
        self.pexp.expect("#")
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("vlan-switch ln_before=" + str(ln_before))
        L.debug("vlan-switch ln_after=" + str(ln_after))
        return parse_vlans(ln_before)

    def get_hostname(self):
        self._enter_enable()
        self.pexp.sendline('show system\r\n')
        self.pexp.expect('Main Power Supply Status')
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("hostname ln_before=" + str(ln_before))
        L.debug("hostname ln_after=" + str(ln_after))
        return parse_host_name(ln_before)

    def set_root_passwd(self, root_pw):
        self._enter_enable()
        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("enable secret {0}\r\n".format(root_pw))
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("exit\r\n")
        self.pexp.expect("#")
        self.pexp.sendline("exit\r\n")
        self.pexp.expect(">")

    def set_hostname(self, hostname):
        self._enter_enable()
        self.pexp.sendline("config\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("hostname {0}\r\n".format(hostname))
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("exit\r\n")
        self.pexp.expect("{0}#".format(hostname))

    # set current time to device
    def set_clock(self):
        from time import strftime, localtime
        self._enter_enable()
        L.debug("set_clock ...")
        self.pexp.sendline("config\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("clock timezone -5 zone UTC\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("clock summer-time recurring first sun apr 2:00 last sun oct 2:00\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("exit\r\n")
        self.pexp.expect("#")
        str_time = strftime("%H:%M:%S %b %d %Y", localtime())
        L.info("clock set {0} ...".format(str_time))
        self.pexp.sendline("clock set {0}\r\n".format(str_time))
        self.pexp.expect("#")
        L.info("clock set DONE")
        return True

    def get_clock(self):
        self._enter_enable()
        L.debug("get_clock ...")
        self.pexp.sendline('show clock\r\n')
        self.pexp.expect(["Time source is","No time source"])
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("get_clock ln_before=" + str(ln_before))
        L.debug("get_clock ln_after=" + str(ln_after))
        return parse_clock_dellpc(ln_before)

    def reset_config(self, port_map):
        ver_num = self.get_version_num()
        vlan_list = self.get_vlans()
        L.info("reset_config vlan list = '{0}'".format(vlan_list))

        #self.pexp.sendcontrol('c')
        hostname = 'Switch'
        self.set_hostname(hostname)
        self._enter_enable()

        self.pexp.sendline("config\r\n")
        self.pexp.expect("\(config\)#")

        L.info("reset interfaces")
        self.pexp.sendline("interface range ethernet all\r\n")
        self.pexp.expect("\(config-if\)#")
        self.pexp.sendline("switchport trunk allowed vlan remove all\r\n")
        self.pexp.expect("\(config-if\)#")
        self.pexp.sendline("switchport mode access\r\n")
        self.pexp.expect("\(config-if\)#")
        self.pexp.sendline("switchport access vlan 1\r\n")
        self.pexp.expect("\(config-if\)#")
        #self.pexp.sendline("mtu 9000\r\n"); self.pexp.expect("\(config-if\)#")
        #self.pexp.sendline("no ip address\r\n"); self.pexp.expect("\(config-if\)#")
        self.pexp.sendline("no shutdown\r\n")
        self.pexp.expect("\(config-if\)#")
        self.pexp.sendline("exit\r\n")
        self.pexp.expect("\(config\)#")

        L.info("reset VLANs")
        for i in vlan_list:
            if (i < 1) or (i > 1000):
                continue
            L.info("reset vlan {0} ...".format(i))
            self.pexp.sendline("interface vlan {0}\r\n".format(i))
            self.pexp.expect("\(config-if\)#")
            self.pexp.sendline("no ip address\r\n")
            self.pexp.expect("\(config-if\)#")
            self.pexp.sendline("exit\r\n")
            self.pexp.expect("\(config\)#")

        L.info("remove vlan record one by one: {0}".format(vlan_list))
        self.pexp.sendline("vlan database\r\n")
        self.pexp.expect("vlan\)#")
        for i in vlan_list:
            if (1 < i) and (i < 1000):
                L.info("no vlan {0} ...".format(i))
                self.pexp.sendline("no vlan {0}\r\n".format(i))
                self.pexp.expect(["vlan\)#"])
        self.pexp.sendline("exit\r\n")
        self.pexp.expect("\(config\)#")

        self.pexp.sendline("exit\r\n")
        self.pexp.expect("#")

        L.info("reset config DONE")
        return True

    # setup the vlan for each port
    def set_vlans(self, port_map, port_list, vlan_list, vlan_set, interface_config={}):
        L.debug("arg_port_map: {0}".format(port_map))
        L.debug("arg_port_list: {0}".format(port_list))
        L.debug("arg_vlan_list: {0}".format(vlan_list))
        L.debug("arg_vlan_set: {0}".format(vlan_set))

        self.set_clock()
        ver_num = self.get_version_num()
        self._enter_enable()

        self.pexp.sendline("config\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("vlan database\r\n")
        self.pexp.expect("vlan\)#")
        for i in vlan_set:
            self.pexp.sendline("vlan {0}\r\n".format(i))
            self.pexp.expect("vlan\)#")

        self.pexp.sendline("exit\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("exit\r\n")
        self.pexp.expect("#")

        vlan_set2 = self.get_vlans()
        vlist2 = [str(element) for element in vlan_set2]
        str_vlans = ",".join(vlist2)

        L.info("setup ports with VLANs ...")
        self.pexp.sendline("config\r\n")
        self.pexp.expect("\(config\)#")
        for i in range(0,len(vlan_list)):
            if vlan_list[i] == 0:
                # setup trunk
                L.info("setup port {0} -> trunk ...".format(port_list[i]))
                self.pexp.sendline("interface ethernet {0}\r\n".format(port_map[port_list[i]]))
                self.pexp.expect("\(config-if\)#")
                #self.pexp.sendline("switchport trunk encapsulation dot1q\r\n")
                #self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport mode trunk\r\n")
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport trunk allowed vlan add {0}\r\n".format(str_vlans))
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("no shutdown\r\n")
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("exit\r\n")
                self.pexp.expect("\(config\)#")
            else:
                # setup vlan
                L.info("setup port {0} -> VLAN {1} ...".format(port_list[i], vlan_list[i]))
                self.pexp.sendline("interface ethernet {0}\r\n".format(port_map[port_list[i]]))
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport mode access\r\n")
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport access vlan {0}\r\n".format(vlan_list[i]))
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("no shutdown\r\n")
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("exit\r\n")
                self.pexp.expect("\(config\)#")

        self.pexp.sendline("exit\r\n")
        self.pexp.expect("#")
        #self.pexp.sendline("exit\r\n"); self.pexp.expect(">")

        self.pexp.sendline("sh vlan\r\n")
        self.pexp.expect("#")
        L.info("set_vlans DONE")
        return True

################################################################################
if __name__ == '__main__':
    import mylog
    L = mylog.setup_custom_logger('switch')

    import unittest
    class myTest(unittest.TestCase):
        output_show_system = """show system
System Description:                       Neyland 24T
System Up Time (days,hour:min:sec):       00,03:01:55
System Contact:                           
System Name:                              home-sw-dellpc5324-1
System Location:                          
System MAC Address:                       00:18:8b:31:42:5f
System Object ID:                         1.3.6.1.4.1.674.10895.3004
Type:                                     PowerConnect 5324

Main Power Supply Status:                 OK
Fan 1 Status:                             OK
Fan 2 Status:                             OK
"""
        output_show_ver ='''sh ver
SW version    2.0.1.4 ( date  01-Aug-2010 time  17:00:12 )
Boot version    1.0.2.02 ( date  23-Jul-2006 time  16:45:47 )
HW version    00.00.02
'''
        output_vlan = """
home-sw-dellpc5324-1# show vlan
Vlan       Name                   Ports                Type     Authorization 
---- ----------------- --------------------------- ------------ ------------- 
 1           1               g(1-24),ch(1-8)          other       Required    


 10         10                                      permanent     Required    
100         100                                     permanent     Required    
            """
        output_int_status = """
home-sw-dellpc5324-1# show int status
                                             Flow Link          Back   Mdix
Port     Type         Duplex  Speed Neg      ctrl State       Pressure Mode
-------- ------------ ------  ----- -------- ---- ----------- -------- -------
g1       1G-Copper      --      --     --     --  Down           --     --    
g2       1G-Copper      --      --     --     --  Down           --     --    
g3       1G-Copper      --      --     --     --  Down           --     --    
g4       1G-Copper      --      --     --     --  Down           --     --    
g5       1G-Copper      --      --     --     --  Down           --     --    
g6       1G-Copper      --      --     --     --  Down           --     --    
g7       1G-Copper      --      --     --     --  Down           --     --    
g8       1G-Copper      --      --     --     --  Down           --     --    
g9       1G-Copper      --      --     --     --  Down           --     --    
g10      1G-Copper      --      --     --     --  Down           --     --    
g11      1G-Copper      --      --     --     --  Down           --     --    
g12      1G-Copper      --      --     --     --  Down           --     --    
g13      1G-Copper      --      --     --     --  Down           --     --    
g14      1G-Copper      --      --     --     --  Down           --     --    
g15      1G-Copper      --      --     --     --  Down           --     --    
g16      1G-Copper      --      --     --     --  Down           --     --    
g17      1G-Copper      --      --     --     --  Down           --     --    
g18      1G-Copper      --      --     --     --  Down           --     --    
g19      1G-Copper    Full    1000  Enabled  Off  Up          Disabled Off    
g20      1G-Copper      --      --     --     --  Down           --     --    
g21      1G-Combo-C     --      --     --     --  Down           --     --    
g22      1G-Combo-C     --      --     --     --  Down           --     --    
g23      1G-Combo-C     --      --     --     --  Down           --     --    
g24      1G-Combo-C   Full    1000  Enabled  Off  Up          Disabled On     

                                          Flow    Link        
Ch       Type    Duplex  Speed  Neg      control  State       
-------- ------- ------  -----  -------- -------  ----------- 
ch1         --     --      --      --       --    Not Present 
ch2         --     --      --      --       --    Not Present 
ch3         --     --      --      --       --    Not Present 
ch4         --     --      --      --       --    Not Present 
ch5         --     --      --      --       --    Not Present 
ch6         --     --      --      --       --    Not Present 
ch7         --     --      --      --       --    Not Present 
ch8         --     --      --      --       --    Not Present 
"""
        def setUp(self):
            pass
        def tearDown(self):
            pass

        def test_parse_model_line(self):
            self.assertEqual('Neyland 24T', parse_model_line(self.output_show_system))

        def test_parse_version_line(self):
            #print("the version is '{0}'.".format(parse_version_line(output)))
            self.assertEqual('2.0.1.4', parse_version_line(self.output_show_ver))

        def test_parse_hostname(self):
            self.assertEqual('home-sw-dellpc5324-1', parse_host_name(self.output_show_system))

        def test_parse_vlans(self):
            self.assertEqual([1,10,100], parse_vlans(self.output_vlan))
            #self.assertEqual([1,5,6,10,20,30,40,50,60,80,90,110,120,1002,1003,1004,1005], parse_vlans(output))

        def test_parse_ports(self):
            self.assertEqual([ 'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'g10', 'g11', 'g12', 'g13', 'g14', 'g15', 'g16', 'g17', 'g18', 'g19', 'g20', 'g21', 'g22', 'g23', 'g24' ], parse_ports(self.output_int_status))

            list1 = [ 'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'g10', 'g11', 'g12', 'g13', 'g14', 'g15', 'g16', 'g17', 'g18', 'g19', 'g20', 'g21', 'g22', 'g23', 'g24' ]
            list2 = ["g"+str(i+1) for i in range(0,24)]
            self.assertEqual(list1, list2)

    unittest.main()

