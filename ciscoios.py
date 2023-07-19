#!/usr/bin/env python3
# encoding: utf8
# -*- coding: utf-8 -*-
#
# The config functions for Cisco IOS
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
from parseclock import parse_clock_ciscoios

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
def parse_version_line(str_version):
    L.debug("version search=" + str(re.search('IOS Software(.*)\s', str_version).group(0)))
    ver_line = re.split(r',', re.search('IOS Software(.*)\s', str_version).group(0))[2].strip()
    return re.split(r' ', ver_line)[1].strip()

def parse_model_line(str_model):
    search1 = re.search('\n.*processor(.*)\s', str_model)
    L.debug("search = {0}".format(search1))
    L.debug("search[0]= {0}".format(search1.group(0)))
    return re.split(r'\(', search1.group(0))[0].strip()

def parse_ports(str_lst):
    port_list = []
    lines = re.split(r'\n', str_lst)
    flg_found = False
    for i in range(0, len(lines)):
        ln = lines[i].strip()
        if ln == '':
            continue
        L.debug("process vlan line: {0}".format(ln))
        L.debug("     vlan line[0]: {0}".format(re.split(r' ', ln)[0]))
        lst = re.split(r' ', ln)
        if len(lst) < 4:
            continue
        port_list.append(lst[0])
    L.debug("parse_ports return list = {0}".format(port_list))
    return port_list

# parse the output of command 'sh vlan-switch brief'
def parse_vlans(str_output):
    vlan_list = []
    lines = re.split(r'\n', str_output)
    flg_found = False
    for i in range(0, len(lines)):
        ln = lines[i].strip()
        if ln == '':
            continue
        if not flg_found:
            if re.search('---- ', ln):
                flg_found = True
            continue
        L.debug("process vlan line: {0}".format(ln))
        L.debug("     vlan line[0]: {0}".format(re.split(r' ', ln)[0]))
        vlan_list.append(int(re.split(r' ', ln)[0]))
    L.debug("parse_vlans return list = {0}".format(vlan_list))
    return vlan_list

def parse_host_name(str_output):
    return re.split(r' ', re.search('hostname (.*)\s*', str_output).group(0))[1].strip()

################################################################################
class CiscoSwitch(Switch):
    def __init__(self):
        super().__init__()

    def _enter_enable(self):
        L.debug("enter to console")
        from switchdevice import pexpect_clean_buffer
        pexpect_clean_buffer(self.pexp)
        self.pexp.sendline("\r\nend\r\n")

        #self.pexp.sendcontrol('c')
        while True:
            L.debug("enter to active prompt ...")
            self.pexp.sendline("\r\n\r\n")
            #self.pexp.sendline('\r\nsh run | i ostname\r\n')
            responses = ["Please answer 'yes' or 'no'","\[yes/no\]:","\[confirm\]","Press RETURN to get started.", ">", "#", pexpect.EOF, pexpect.TIMEOUT]
            ret = self.pexp.expect(responses, timeout=5)
            #if ret < 6:
            #    ln_before = self.pexp.before.decode('UTF-8')
            #    ln_after = self.pexp.after.decode('UTF-8')
            #    L.info("enter_enable ln_before=" + str(ln_before))
            #    L.info("enter_enable ln_after=" + str(ln_after))
            #    L.info("got response: {0}".format(responses[ret]))
            if ret == 0:
                L.debug("send 'no' ...")
                self.pexp.sendline("no\r\n")
            elif ret == 1:
                L.debug("send 'no' ...")
                self.pexp.sendline("no\r\n")
            elif ret == 2:
                self.pexp.sendline("\r\n")
            elif ret == 3:
                L.debug("i need a RETURN!!")
                continue
            elif ret == 4:
                L.debug("enter to enable ...")
                self.pexp.sendline("\r\nenable\r\n\r\n")
            elif ret == 5:
                L.debug("got a '#'")
                break
            else:
                L.debug("got eof/timeout")
                pass
            time.sleep(2)

        self.pexp.sendline("terminal width 512\r\n")
        self.pexp.sendline("terminal length 512\r\n")
        L.debug("done, it's in 'enable' state")

    def _quit_enable(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline('end\r\n')
        self.pexp.sendline("exit\r\n")
        #self.pexp.expect(["Press RETURN to get started."])
        self.pexp.sendline()

    # save the current config to disk
    def save_config(self):
        self._enter_enable()
        L.info("copy config run -> startup ...")
        self.pexp.sendline("copy running-config startup-config\r\n")
        ret = self.pexp.expect(["The copy operation was completed successfully","Destination filename \[startup-config\]?"])
        if ret == 1:
            self.pexp.sendline("\r\n")
            self.pexp.expect(["\[OK\]","#"])

    # reboot system
    def reboot(self, wait_network=True):
        if self.is_gns3:
            L.warning("Skipped: GNS3 don't support cisco IOS reload command.")
            return True

        self._enter_enable()

        L.info("reload ...")
        self.pexp.sendline("reload\r\n")
        while True:
            ret = self.pexp.expect(["\[yes/no\]","\[confirm\]"])
            if ret == 0:
                self.pexp.sendline("yes\r\n")
            else:
                self.pexp.sendline("\r\n")
                break
        L.info("waiting for reload ...")
        ret = self.pexp.expect(["enter the initial configuration dialog", "Press RETURN to get started", "Cisco IOS Software"])
        if ret == 0:
            self.pexp.sendline("n\r\n")
        self.pexp.sendline("\r\n")

        L.info("reboot() DONE")

    def get_model_name(self):
        self._enter_enable()
        L.info("get_model_name() get version")
        self.pexp.sendline('sh ver | i ytes of memory\r\n')
        L.info("wait memory")
        self.pexp.expect('bytes of memory')
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("model ln_before=" + str(ln_before))
        L.debug("model ln_after=" + str(ln_after))
        L.info("parse model")
        return parse_model_line(ln_before)

    def get_version(self):
        self._enter_enable()
        L.info("get version")
        self.pexp.sendline('sh ver | i IOS\r\n')
        #time.sleep(3)
        self.pexp.expect('RELEASE SOFTWARE')
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("version ln_before=" + str(ln_before))
        L.debug("version ln_after=" + str(ln_after))
        return parse_version_line(ln_before)

    def show_info(self):
        self._enter_enable()
        self.pexp.sendline('term len 0\r\n')
        port_list = self.get_ports()
        L.info("get port_list: {0}".format(port_list))
        #self.pexp.sendline('show tech\r\n')

    def get_version_num(self):
        ver = self.get_version()
        return float(re.split(r'\(', ver)[0].strip())

    def get_hostname(self):
        self._enter_enable()
        L.info("get hostname")
        self.pexp.sendline('sh run | i ostname\r\n')
        self.pexp.expect('hostname .*[\r\n]+')
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("hostname ln_before=" + str(ln_before))
        L.debug("hostname ln_after=" + str(ln_after))
        return parse_host_name(ln_after)

    def set_hostname(self, hostname):
        self._enter_enable()
        L.info("set hostname {0} ...".format(hostname))
        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("hostname {0}\r\n".format(hostname))
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("exit\r\n")

    def set_root_passwd(self, root_pw):
        self._enter_enable()
        L.info("set root pw")
        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("enable secret {0}\r\n".format(root_pw))
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("exit\r\n")
        #self._quit_enable()

    # get a list of ports
    def get_ports(self):
        self._enter_enable()
        self.pexp.sendline("show int status\r\n")
        self.pexp.expect("Port[\s]+Name[\s]+Status[\s]+Vlan[\s]+Duplex[\s]+Speed[\s]+Type")
        self.pexp.expect("#")
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("vlan-switch ln_before=" + str(ln_before))
        L.debug("vlan-switch ln_after=" + str(ln_after))
        return parse_ports(ln_before)

    # get a list of vlan
    def get_vlans(self):
        # command to show vlan info: show int vlan 1
        ver_num = self.get_version_num()

        self._enter_enable()
        L.info("get vlans")

        if ver_num < 15:
            self.pexp.sendline("sh vlan-switch brief\r\n")
            self.pexp.expect("VLAN Name")
            self.pexp.expect("1002 fddi-default")
        else:
            self.pexp.sendline("show vlan\r\n")
            self.pexp.expect("VLAN Name")
            self.pexp.expect("1002 fddi-default")
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("vlan-switch ln_before=" + str(ln_before))
        L.debug("vlan-switch ln_after=" + str(ln_after))
        return parse_vlans(ln_before)

    # set current time to device
    def set_clock(self):
        from time import strftime, localtime
        self._enter_enable()
        L.debug("set_clock ...")
        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("clock timezone EST -5\r\n")
        self.pexp.expect("\(config\)#")
        #self.pexp.sendline("clock summer-time EDT recurring first sun apr 02:00 last sun oct 02:00\r\n")
        self.pexp.sendline("clock summer-time EDT recurring\r\n")
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
        self.pexp.sendline('show clock detail\r\n')
        self.pexp.expect(["Time source is","No time source"])
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        L.debug("get_clock ln_before=" + str(ln_before))
        L.debug("get_clock ln_after=" + str(ln_after))
        return parse_clock_ciscoios(ln_before)

    def reset_config(self, port_map):
        ver_num = self.get_version_num()
        vlan_list = self.get_vlans()
        L.debug("get vlan_list: {0}".format(vlan_list))
        port_list = self.get_ports()
        L.debug("get port_list: {0}".format(port_list))

        hostname = 'Switch'
        self.set_hostname(hostname)

        self._enter_enable()
        L.info("reset config")

        L.info("reset interfaces")
        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")
        for p in port_list:
            L.info("reset interface {0} ...".format(p))
            self.pexp.sendline("interface {0}\r\n".format(p))
            self.pexp.expect("\(config-if\)#")
            self.pexp.sendline("switchport trunk allowed vlan remove 1-1000\r\n")
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

        self.pexp.sendline("exit\r\n")
        self.pexp.expect("#")

        L.info("remove vlan record one by one")
        if ver_num < 15:
            self.pexp.sendline("vlan database\r\n")
            self.pexp.expect("\(vlan\)#")
            for i in vlan_list:
                if (i > 1) and (i < 1000):
                    L.info("no vlan {0} ...".format(i))
                    self.pexp.sendline("no vlan {0}\r\n".format(i))
                    self.pexp.expect("\(vlan\)#")
                else:
                    L.info("skip vlan {0}".format(i))

            self.pexp.sendline("exit\r\n")

        else:
            L.debug("config t ...")
            self.pexp.sendline("config t\r\n")
            L.debug("expect (config)# ...")
            self.pexp.expect("\(config\)#")
            for i in vlan_list:
                if (i > 1) and (i < 1000):
                    L.info("no vlan {0} ...".format(i))
                    self.pexp.sendline("no vlan {0}\r\n".format(i))
                    L.debug("expect (config)# ...")
                    self.pexp.expect("\(config\)#")
            self.pexp.sendline("exit\r\n")
        L.info("reset config DONE")
        return True

    def reset_config_hw(self, port_map):
        hostname = 'Switch'
        self.set_hostname(hostname)
        self._enter_enable()

        L.info("clear config all ...")
        self.pexp.sendline("clear config all\r\n")
        ret = self.pexp.expect(["continue \(y/n\)", "Invalid input detected at"])
        if ret == 0:
            self.pexp.sendline("y\r\n")
            self.pexp.expect("configuration cleared")

        L.info("erase startup-config ...")
        self.pexp.sendline("erase startup-config\r\n")
        ret = self.pexp.expect(["\[confirm\]", "Invalid input detected at"])
        if ret == 0:
            self.pexp.sendline("\r\n")
            self.pexp.expect(["{0}#".format(hostname),"complete"])

        L.info("write erase ...")
        self.pexp.sendline("write erase\r\n")
        ret = self.pexp.expect(["\[confirm\]", "Invalid input detected at"])
        if ret == 0:
            self.pexp.sendline("y\r\n")
            self.pexp.expect("complete")

        self.reboot()
        self._enter_enable()

        L.info("delete the VLAN database file ...")
        self.pexp.sendline("delete flash:vlan.dat\r\n")
        self.pexp.expect("elete .*vlan.dat") #self.pexp.expect("\[confirm\]")
        self.pexp.sendline("\r\n")
        self.pexp.expect(["elete .*vlan.dat","Error deleting flash:/vlan.dat"])
        self.pexp.sendline("\r\n")
        self.pexp.expect("#")

        self.reboot()
        self._enter_enable()

        L.info("reset_config_hw DONE")
        return True

    # setup the vlan for each port
    def set_vlans(self, port_map, port_list, vlan_list, vlan_set, interface_config={}):
        self.set_clock()
        ver_num = self.get_version_num()

        self._enter_enable()
        L.info("set vlans")

        L.info("add VLAN to database ...")
        if ver_num < 15:
            self.pexp.sendline("vlan database\r\n")
            self.pexp.expect("\(vlan\)#")
            for i in vlan_set:
                if i < 2:
                    # ignore
                    continue
                L.info("add VLAN {0} ...".format(i))
                self.pexp.sendline("vlan {0}\r\n".format(i))
                self.pexp.expect("\(vlan\)#")

            self.pexp.sendline("exit\r\n")
            self.pexp.expect("#")
        else:
            # add vlan
            self.pexp.sendline("config t\r\n")
            self.pexp.expect("\(config\)#")
            for i in vlan_set:
                if i < 2:
                    # ignore
                    continue
                L.info("add VLAN {0} ...".format(i))
                self.pexp.sendline("add vlan {0}\r\n".format(i))
                self.pexp.expect("\(config\)#")
            self.pexp.sendline("exit\r\n")
            self.pexp.expect("#")

        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")

        assert(not port_map == None)
        assert(len(port_map) > 0)

        L.info("assign port to VLAN ...")
        for i in range(0,len(vlan_list)):
            if vlan_list[i] < 0:
                # ignore
                continue
            if vlan_list[i] == 0:
                # setup trunk
                L.info("add {0} as trunk ...".format(port_map[port_list[i]]))
                self.pexp.sendline("int {0}\r\n".format(port_map[port_list[i]]))
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport trunk encapsulation dot1q\r\n")
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport mode trunk\r\n")
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("exit\r\n")
                self.pexp.expect("\(config\)#")
            else:
                # setup vlan
                L.info("add {0} to VLAN {1} ...".format(port_map[port_list[i]],vlan_list[i]))
                self.pexp.sendline("int vlan {0}\r\n".format(vlan_list[i]))
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("exit\r\n")
                self.pexp.expect("\(config\)#")
                self.pexp.sendline("int {0}\r\n".format(port_map[port_list[i]]))
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport mode access\r\n")
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("switchport access vlan {0}\r\n".format(vlan_list[i]))
                self.pexp.expect("\(config-if\)#")
                self.pexp.sendline("exit\r\n")
                self.pexp.expect("\(config\)#")

        self.pexp.sendline("end\r\n")
        self.pexp.expect("#")

        # show VLAN
        self.pexp.sendline("sh vlan-switch brief\r\n")
        self.pexp.sendline("sh vlans\r\n")
        self.pexp.sendline("sh vlan\r\n")
        self.pexp.expect(["Invalid input detected at","#"])

        self.pexp.sendline("show interfaces trunk\r\n")
        self.pexp.expect("#")
        self.pexp.sendline("show interface status\r\n")
        self.pexp.expect("#")

        self.pexp.sendline("show mac\r\n")
        self.pexp.sendline("show mac address\r\n")
        self.pexp.expect("#")

        L.info("set vlans DONE")
        return True

################################################################################
if __name__ == '__main__':
    import mylog
    L = mylog.setup_custom_logger('switch')

    import unittest
    class myTest(unittest.TestCase):

        def setUp(self):
            pass
        def tearDown(self):
            pass

        def test_parse_model_line(self):
            self.assertEqual('Cisco 3640', parse_model_line("""Switch#sh ver | i ytes of memory
Cisco 3640 (R4700) processor (revision 0xFF) with 187392K/9216K """))

        def test_parse_version_line(self):
            self.assertEqual('12.4(25c)', parse_version_line('Cisco IOS Software, 3600 Software (C3640-IK9O3S-M), Version 12.4(25c), RELEASE SOFTWARE (fc2)'))

        def test_parse_hostname(self):
            self.assertEqual('Switch', parse_host_name('hostname Switch'))

        def test_parse_vlans(self):
            output = """Switch#show vlan-switch brief
VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/0, Fa0/6, Fa0/7, Fa0/8
5    VLAN0005                         active    Fa0/2
6    VLAN0006                         active    Fa0/1
10   VLAN0010                         active    Fa0/3
20   VLAN0020                         active    Fa0/4
30   VLAN0030                         active    Fa0/5
40   VLAN0040                         active    Fa0/9
50   VLAN0050                         active    Fa0/10
60   VLAN0060                         active    Fa0/12
80   VLAN0080                         active    Fa0/13
90   VLAN0090                         active    Fa0/14
110  VLAN0110                         active    Fa0/15
120  VLAN0120                         active    Fa0/11
1002 fddi-default                     active    
1003 token-ring-default               active    
1004 fddinet-default                  active    
1005 trnet-default                    active    
            """
            self.assertEqual([1,5,6,10,20,30,40,50,60,80,90,110,120,1002,1003,1004,1005], parse_vlans(output))

        def test_parse_vlans2(self):
            output = """                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Fa0/1, Fa0/2, Fa0/3, Fa0/4, Fa0/5, Fa0/6, Fa0/7, Fa0/8, Gi0/1
6    mgmt                             active    
100  netlab                           active    
"""
            L.info("output={0}".format(output))
            self.assertEqual([1,6,100], parse_vlans(output))

        def test_parse_ports(self):
            output="""
Fa0/1                        connected    20         a-full  a-100 10/100BaseTX
Fa0/2                        connected    100        a-full  a-100 10/100BaseTX
Fa0/3                        notconnect   100          auto   auto 10/100BaseTX
Fa0/4                        notconnect   100          auto   auto 10/100BaseTX
Fa0/5                        notconnect   100          auto   auto 10/100BaseTX
Fa0/6                        notconnect   100          auto   auto 10/100BaseTX
Fa0/7                        notconnect   100          auto   auto 10/100BaseTX
Fa0/8                        notconnect   100          auto   auto 10/100BaseTX
Gi0/1                        connected    trunk      a-full a-1000 10/100/1000BaseTX
Switch
"""
            L.info("output={0}".format(output))
            exp = ["Fa0/1","Fa0/2","Fa0/3","Fa0/4","Fa0/5","Fa0/6","Fa0/7","Fa0/8","Gi0/1",]
            self.assertEqual(exp, parse_ports(output))

    unittest.main()
