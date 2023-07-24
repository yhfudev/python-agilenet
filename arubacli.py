#!/usr/bin/env python3
# encoding: utf8
# -*- coding: utf-8 -*-
#
# The config functions for HP/Aruba J9727A
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
from parseclock import parse_clock_arubacli

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
def parse_version_line(str_output):
    search1 = re.search('Boot ROM Version(.*)', str_output)
    L.debug("search = {0}".format(search1))
    L.debug("search[0]= {0}".format(search1.group(0)))
    return re.split(r':', search1.group(0))[1].strip()

# show system
def parse_hostname_line(str_output):
    search1 = re.search('\n.*System Name(.*)\s', str_output)
    L.debug("search = {0}".format(search1))
    L.debug("search[0]= {0}".format(search1.group(0)))
    return re.split(r':', search1.group(0))[1].strip()

# show dhcp client vendor-specific
def parse_model_line2(str_output):
    search1 = re.search('Vendor Class Id (.*)\s', str_output)
    L.debug("search = {0}".format(search1))
    L.debug("search[0]= {0}".format(search1.group(0)))
    str1 = re.split(r'=', search1.group(0))[1].strip()
    return str1.replace(' dslforum.org', '')

# show modules
def parse_model_line3(str_output):
    search1 = re.search('.*Chassis(.*)\s', str_output)
    L.debug("search = {0}".format(search1))
    L.debug("search[0]= {0}".format(search1.group(0)))
    str1 = re.split(r':', search1.group(0))[1].strip()
    return str1.replace('Serial Number', '').strip()

def parse_ports(str_output):
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
        if len(lst) < 3:
            L.warning("not a item: {0}".format(lst))
            break
        vlan_list.append(lst[0])
    L.debug("parse vlan list = {0}".format(vlan_list))
    vlan_list = [int(i) for i in vlan_list]
    return vlan_list

def parse_host_name(str_output):
    return re.split(r'"', re.search('hostname (.*)\s*', str_output).group(0))[1].strip()

################################################################################
class ArubaSwitch(Switch):
    def __init__(self):
        super().__init__()

    def _enter_enable(self):
        L.debug("enter to console")
        self.pexp.sendline("\r\n\r\nend\r\n\r\n")

        #self.pexp.sendcontrol('c')
        while True:
            L.debug("enter to active prompt ...")
            self.pexp.sendline("\r\n\r\n\r\n\r\n\r\n\r\n")
            #self.pexp.sendline('\r\nsh run | i ostname\r\n')
            responses = [
                "Please answer 'yes' or 'no'",
                "\[yes/no\]:",
                "\[confirm\]",
                "Press RETURN to get started.",
                "Processing of Vendor Specific Configuration",
                ">",
                "#",
                pexpect.EOF,
                pexpect.TIMEOUT]
            ret = self.pexp.expect(responses, timeout=5)
            #ret = self.pexp.expect(responses)
            #if ret < 6:
            #    ln_before = self.pexp.before.decode('UTF-8')
            #    ln_after = self.pexp.after.decode('UTF-8')
            #    L.info("enter_enable ln_before=" + str(ln_before))
            #    L.info("enter_enable ln_after=" + str(ln_after))
            #    L.info("got response: {0}".format(responses[ret]))
            if ret < 2:
                L.debug("send 'no' ...")
                self.pexp.sendline("no\r\n")
            elif ret < 5:
                self.pexp.sendline("\r\n")
            elif ret == 5:
                L.debug("enter to enable ...")
                self.pexp.sendline("\r\nenable\r\n\r\n")
            elif ret == 6:
                L.debug("got a '#'")
                break
            elif responses[ret] == pexpect.TIMEOUT:
                L.debug("got eof/timeout")
                self.pexp.sendline("\r\n")
            else:
                L.debug("got eof/timeout")
                self.pexp.sendline("\r\n")
            time.sleep(2)

        self.pexp.sendline("terminal width 512\r\n")
        self.pexp.sendline("terminal length 512\r\n")
        L.debug("done, it's in 'enable' state")

    def _quit_enable(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline('end\r\n')
        self.pexp.sendline("exit\r\n")
        ret = self.pexp.expect(["\(y/n\)","\(yes/no\)","\[yes/no\]", "\[confirm\]","Press RETURN to get started.",">","#"])
        if ret < 1:
            self.pexp.sendline("y")
        self.pexp.sendline()

    # save the current config to disk
    def save_config(self):
        self._enter_enable()
        L.info("save_config ...")
        #self.pexp.sendline("copy startup-config default-config\r\n")
        self.pexp.sendline("write memory")
        L.info("save_config DONE.")
        self.pexp.expect(["#"])

    def _wait_reboot(self):
        exp_list = [
            "\(y/n\)","\(yes/no\)","\[yes/no\]", "\[confirm\]",
            "Rebooting the System", "Initialization done", "Waiting for Speed Sense", "Press any key to continue",
            pexpect.EOF, pexpect.TIMEOUT]
        while True:
            ret = self.pexp.expect(exp_list, timeout=15)
            if ret < 3:
                L.info("send 'y' for '{0}' ...".format(exp_list[ret]))
                self.pexp.sendline("y")
            elif ret < 7:
                L.info("get expect messages ...")
                self.pexp.sendline("\r\n")
            elif exp_list[ret] == pexpect.TIMEOUT:
                L.info("timeout, waiting for console ...")
                self.pexp.sendline("\r\n")
            else:
                L.info("it's time to enter console ...")
                break
        self.pexp.sendline("\r\n\r\n\r\n")
        self._enter_enable()

    # reboot system
    def reboot(self, wait_network=True):
        self._enter_enable()
        L.info("reload ...")
        self.pexp.sendline("reload")
        self._wait_reboot()

        L.info("reboot() DONE")

    def get_board(self):
        self._enter_enable()
        L.info("get_model_name() get version")
        self._esc_console()

        self.pexp.sendline('show modules')
        self._nor_console()

        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        # L.debug("model ln_before=" + str(ln_before))
        # L.debug("model ln_after=" + str(ln_after))

        self._end_console()
        return parse_model_line3(ln_before)

    def get_model_name(self):
        self._enter_enable()
        L.info("get_model_name() get version")
        self._esc_console()

        self.pexp.sendline('\r\nshow dhcp client vendor-specific\r\n')
        self._nor_console()

        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        # L.debug("model ln_before=" + str(ln_before))
        # L.debug("model ln_after=" + str(ln_after))

        self._end_console()
        return parse_model_line2(ln_before)

    def get_version(self):
        self._enter_enable()
        L.info("get version")
        self.pexp.sendline('show ver\r\n')
        #time.sleep(3)
        self.pexp.expect('Boot Image')
        self.pexp.expect('Active Boot ROM')
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        # L.info("version ln_before=" + str(ln_before))
        # L.debug("version ln_after=" + str(ln_after))
        return parse_version_line(ln_before)

    def show_info(self):
        self._enter_enable()
        self.pexp.sendline('term len 0\r\n')
        port_list = self.get_ports()
        L.info("get port_list: {0}".format(port_list))
        #self.pexp.sendline('show tech\r\n')
        # show tech buffers

    def get_version_num(self):
        ver = self.get_version()
        lst = re.split(r'\.', ver)
        return float(lst[1].strip() + "." + lst[2].strip())

    def get_hostname(self):
        self._enter_enable()
        L.info("get hostname")

        # self.pexp.sendline('show system\r\n')
        # self.pexp.expect('Status and Counters')
        # self.pexp.expect('System Contact')
        # parse_hostname_line(ln_before)

        self.pexp.sendline('sh run | i ostname\r\n')
        self.pexp.expect('hostname .*[\r\n]+')
        #ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        #L.debug("hostname ln_before=" + str(ln_before))
        #L.debug("hostname ln_after=" + str(ln_after))
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
        # Port     Name       Status
        self.pexp.expect("Port[\s]+Name[\s]+Status")
        self.pexp.expect("#")
        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        # L.debug("vlan-switch ln_before=" + str(ln_before))
        # L.debug("vlan-switch ln_after=" + str(ln_after))
        return parse_ports(ln_before)

    # get a list of vlan
    def get_vlans(self):
        # command to show vlan info: show int vlan 1
        #ver_num = self.get_version_num()
        hostname = self.get_hostname()

        self._enter_enable()
        L.info("get vlans")

        self.pexp.sendline("show vlan\r\n")
        self.pexp.expect("VLAN ID")
        self.pexp.expect("{0}#".format(hostname))

        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        # L.debug("vlan-switch ln_before=" + str(ln_before))
        # L.debug("vlan-switch ln_after=" + str(ln_after))
        return parse_vlans(ln_before)

    # set current time to device
    def set_clock(self):
        from time import strftime, localtime
        self._enter_enable()
        L.info("set_clock ...")
        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")
        L.debug("clock timezone EST -5")
        self.pexp.sendline("clock timezone EST -5\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("clock summer-time EST recurring 2 Sun Mar 2:00 first Sun Nov 3:00 -5\r\n")
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("time daylight-time-rule continental-us-and-canada\r\n")
        self.pexp.expect("\(config\)#")
        #(config)#clock set 01/13/2001 00:01:02
        str_time = strftime("%m/%d/%Y %H:%M:%S", localtime())
        L.info("clock set {0} ...".format(str_time))
        self.pexp.sendline("clock set {0}\r\n".format(str_time))
        self.pexp.expect("\(config\)#")
        self.pexp.sendline("exit\r\n")
        self.pexp.expect("#")
        L.info("clock set DONE")
        return True

    def _esc_console(self):
        self.pexp.sendline('\r\nend\r\n')
        self.pexp.sendline('config')
        self.pexp.expect("\(config\)#")

        #self.pexp.sendline('console terminal ans'); self.pexp.expect("\(config\)#")
        self.pexp.sendline('console local-terminal none'); self.pexp.expect("\(config\)#")

        from switchdevice import pexpect_clean_buffer; pexpect_clean_buffer(self.pexp)
        pass

    def _nor_console(self):
        self.pexp.sendline('console local-terminal ansi'); self.pexp.expect(["tty=ansi", "Invalid input: console"], timeout=2)
        pass

    def _end_console(self):
        self.pexp.sendline('console local-terminal vt100'); self.pexp.expect("\(config\)#")
        self.pexp.sendline('exit')
        pass

    def get_clock(self):
        self._enter_enable()
        L.debug("get_clock ...")

        self._esc_console()
        #L.debug("show time ...")

        self.pexp.sendline('show time\r\n')
        self._nor_console()

        ln_before = self.pexp.before.decode('UTF-8')
        ln_after = self.pexp.after.decode('UTF-8')
        #import hexdump
        #L.debug("get_clock ln_before="); hexdump.hexdump(bytes(ln_before, 'utf-8'))
        #L.debug("get_clock ln_after="); hexdump.hexdump(bytes(ln_after, 'utf-8'))

        self._end_console()
        return parse_clock_arubacli(ln_before)

    def reset_config(self, port_map):
        return False # debug
        return self.reset_config_sw(port_map)
        #return self.reset_config_hw()
        #return True #debug
        #self.reset_config_hw() ; return False #debug

    # remove all of interfaces and VLANs
    def reset_config_sw(self, port_map):
        ver_num = self.get_version_num()
        L.debug("ver num: {0}".format(ver_num))
        vlan_list = self.get_vlans()
        L.debug("get vlan_list: {0}".format(vlan_list))
        port_list = self.get_ports()
        L.debug("get port_list: {0}".format(port_list))
        str_ports = ",".join(port_list)

        hostname = 'Switch'
        self.set_hostname(hostname)

        self._enter_enable()
        L.info("reset config")

        L.info("reset interfaces")
        self.pexp.sendline("config t\r\n")
        L.info("reset interface {0} vlan".format(str_ports))
        for v in vlan_list:
            L.info("no vlan {0} tagged {1} ...".format(v,str_ports))
            self.pexp.sendline("no vlan {0} tagged {1}\r\n".format(v,str_ports))
            self.pexp.expect("\(config\)#")
            self.pexp.sendline("no vlan {0} untagged {1}\r\n".format(v,str_ports))
            self.pexp.expect("\(config\)#")
        self.pexp.sendline("vlan 1 untagged {0}\r\n".format(str_ports))
        self.pexp.expect("\(config\)#")

        self.pexp.sendline("interface ethernet {0}\r\n".format(str_ports))
        self.pexp.expect("\(eth-")
        self.pexp.sendline("enable\r\n")
        self.pexp.expect("\(eth-")
        self.pexp.sendline("exit\r\n")
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

    # factory reset
    def reset_config_hw(self):
        self._enter_enable()

        L.info("clear config all ...")
        self.pexp.sendline("erase startup-config\r\n")
        self._wait_reboot()

        L.info("reset_config_hw DONE")
        return True

    # setup the vlan for each port
    def set_vlans(self, port_map, port_list, vlan_list, vlan_set, interface_config={}):
        self.set_clock()
        ver_num = self.get_version_num()

        self._enter_enable()
        L.info("set vlans")

        L.info("add VLAN to database ...")
        # add vlan
        self.pexp.sendline("config t\r\n")
        self.pexp.expect("\(config\)#")
        for i in vlan_set:
            if i < 2:
                # ignore
                continue
            L.info("add VLAN {0} ...".format(i))
            self.pexp.sendline("vlan {0}\r\n".format(i))
            self.pexp.expect("\(vlan-{0}\)#".format(i))
            self.pexp.sendline("exit\r\n")
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
                for j in vlan_set:
                    self.pexp.sendline("vlan {1} tagged {0}\r\n".format(port_map[port_list[i]],j))
                self.pexp.expect("\(config\)#")
            else:
                # setup vlan
                L.info("add {0} to VLAN {1} ...".format(port_map[port_list[i]],vlan_list[i]))
                self.pexp.sendline("vlan {1} untagged {0}\r\n".format(port_map[port_list[i]],vlan_list[i]))
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

        def test_parse_hostname(self):
            self.assertEqual('HP-2920-24G-PoEP', parse_hostname_line("""HP-2920-24G-PoEP# show system | i System Name
  System Name        : HP-2920-24G-PoEP           """))

        def test_parse_model_line2(self):
            self.assertEqual('HP J9727A 2920-24G-PoE+ Switch', parse_model_line2("""#show dhcp client vendor-specific
Vendor Class Id = HP J9727A 2920-24G-PoE+ Switch dslforum.org
Processing of Vendor Specific Configuration is enabled"""))


        def test_parse_model_line3(self):
            self.assertEqual('2920-24G-PoE+  J9727A', parse_model_line3("""#show modules

 Status and Counters - Module Information

  Chassis: 2920-24G-PoE+  J9727A         Serial Number:   SG35FLX0QV


  Slot  Module Description                         Serial Number    Status    
  ----- ------------------------------------------ ---------------- ----------
"""))

        def test_parse_version_line(self):
            self.assertEqual('WB.16.03', parse_version_line('Boot ROM Version:    WB.16.03'))

        def test_parse_hostname(self):
            self.assertEqual('HP-2920-24G-PoEP', parse_host_name('hostname "HP-2920-24G-PoEP"'))

        def test_parse_vlans(self):
            output = """HP-2920-24G-PoEP# show vlan

 Status and Counters - VLAN Information

  Maximum VLANs to support : 256                  
  Primary VLAN : DEFAULT_VLAN
  Management VLAN :             

  VLAN ID Name                             | Status     Voice Jumbo
  ------- -------------------------------- + ---------- ----- -----
  1       DEFAULT_VLAN                     | Port-based No    No   
"""

            output2 = """Switch# show vlan

 Status and Counters - VLAN Information

  Maximum VLANs to support : 256                  
  Primary VLAN : DEFAULT_VLAN
  Management VLAN :             

  VLAN ID Name                             | Status     Voice Jumbo
  ------- -------------------------------- + ---------- ----- -----
  1       DEFAULT_VLAN                     | Port-based No    No   
  2       VLAN2                            | Port-based No    No   
  5       VLAN5                            | Port-based No    No   
  6       VLAN6                            | Port-based No    No   
  20      VLAN20                           | Port-based No    No   
  60      VLAN60                           | Port-based No    No   
  90      VLAN90                           | Port-based No    No   
  100     VLAN100                          | Port-based No    No   
  110     VLAN110                          | Port-based No    No   
"""
            self.assertEqual([1], parse_vlans(output))
            self.assertEqual([1,2,5,6,20,60,90,100,110], parse_vlans(output2))

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
            output1="""HP-2920-24G-PoEP# show int brief

 Status and Counters - Port Status

                          | Intrusion                           MDI  Flow Bcast
  Port         Type       | Alert     Enabled Status Mode       Mode Ctrl Limit
  ------------ ---------- + --------- ------- ------ ---------- ---- ---- -----
  1            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  2            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  3            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  4            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  5            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  6            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  7            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  8            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  9            100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  10           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  11           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  12           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  13           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  14           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  15           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  16           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  17           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  18           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  19           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  20           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  21           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  22           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  23           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
  24           100/1000T  | No        Yes     Down   1000FDx    Auto off  0    
HP-2920-24G-PoEP
"""
            output2="""
HP-2920-24G-PoEP# show int

 Status and Counters - Port Counters

                                                                 Flow Bcast
  Port         Total Bytes    Total Frames   Errors Rx Drops Tx  Ctrl Limit
  ------------ -------------- -------------- --------- --------- ---- -----
  1            0              0              0         0         off  0    
  2            0              0              0         0         off  0    
  3            0              0              0         0         off  0    
  4            0              0              0         0         off  0    
  5            0              0              0         0         off  0    
  6            0              0              0         0         off  0    
  7            0              0              0         0         off  0    
  8            0              0              0         0         off  0    
  9            0              0              0         0         off  0    
  10           0              0              0         0         off  0    
  11           0              0              0         0         off  0    
  12           0              0              0         0         off  0    
  13           0              0              0         0         off  0    
  14           0              0              0         0         off  0    
  15           0              0              0         0         off  0    
  16           0              0              0         0         off  0    
  17           0              0              0         0         off  0    
  18           0              0              0         0         off  0    
  19           0              0              0         0         off  0    
  20           0              0              0         0         off  0    
  21           0              0              0         0         off  0    
  22           0              0              0         0         off  0    
  23           0              0              0         0         off  0    
  24           0              0              0         0         off  0   
HP-2920-24G-PoEP
"""
            ports_list = [str(i+1) for i in range(0,24)]
            L.info("output={0}".format(output1))
            self.assertEqual(ports_list, parse_ports(output1))
            L.info("output={0}".format(output2))
            self.assertEqual(ports_list, parse_ports(output2))

    unittest.main()
