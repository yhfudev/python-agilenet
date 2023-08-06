#!/usr/bin/env python3
# encoding: utf8
# -*- coding: utf-8 -*-
#
# setup network equipments
#
# Copyright 2016-2021 Yunhui Fu <yhfudev@gmail.com>
#
__author__ = 'Yunhui Fu'
__version__ = 'v0.1.1'
__license__ = 'GPLv3'

import io
import os
import sys
import random
import argparse # argparse > optparse > getopt
import logging as L
import csv
from datetime import datetime
from datetime import timedelta
import ipaddress
import time
import pyjson5

import pexpect
import serial
from pexpect_serial import SerialSpawn

import logging
import mylog
L = mylog.setup_custom_logger('switch')
L.setLevel(logging.INFO)

from switchdevice import Switch, port_vlan_to_lists
from openwrtuci import OpenwrtSwitch, VlanPortGenerator
from ciscoios import CiscoSwitch
from dellpc import DellSwitch
from arubacli import ArubaSwitch

try:
    FileNotFoundError # python 3
except NameError:
    FileNotFoundError = IOError # python 2

if sys.version_info[0] >= 3:
    unicode = str

PROGRAM_PREFIX = os.path.basename(__file__).split('.')[0]

################################################################################
# example config_device
#config_device_1 = {
#    'name': 'Cisco-netlab-gns3',
#    'driver': 'ciscoios',
#    #'arg_has_hw_switch': True, # ignored
#}
def factory_device(config_device):
    device = None
    if config_device['driver'] == 'ciscoios':
        L.debug('return CiscoSwitch')
        device = CiscoSwitch()
    elif config_device['driver'] == 'openwrtuci':
        L.debug('return OpenwrtSwitch')
        device = OpenwrtSwitch()
    elif config_device['driver'] == 'dellpc':
        L.debug('return DellSwitch')
        device = DellSwitch()
    elif config_device['driver'] == 'arubacli':
        L.debug('return ArubaSwitch')
        device = ArubaSwitch()

    if device:
        if ('arg_has_hw_switch' in config_device) and config_device['arg_has_hw_switch']:
            device.has_hw_switch = True
        else:
            device.has_hw_switch = False

        # check the port_map, make sure that if the config["arg_has_hw_switch"]==True, the config["arg_port_map"]["CPU"] should not be [None,None]
        if device.has_hw_switch:
            if not config_device['arg_port_map']['CPU']:
                L.error(f"The hardware switch is configured, but there's no 'CPU' entry in the port map.")
                L.warning(f"The code will automatically revert to the configuration of no hardware switch.")
                device.has_hw_switch = False
            if not config_device['arg_port_map']['CPU'][0]:
                L.error(f"The hardware switch is configured, but the port map for 'CPU' is not set up to a specific switch port.")
                L.warning(f"The code will automatically revert to the configuration of no hardware switch.")
                device.has_hw_switch = False

        if ('arg_is_gns3' in config_device) and config_device['arg_is_gns3']:
            device.is_gns3 = True
        else:
            device.is_gns3 = False

    return device


class PexpectWrapper():
    def __del__(self):
        if self._fp != sys.stdout:
            self._fp.close()

    def __init__(self, pexp, filename):
        #add properties etc.
        self._pexp = pexp
        self._fp = None
        if filename == "/dev/stderr":
            self._fp = sys.stdout
        else:
            self._fp = open(filename, "a")

    def __str__(self):
        return self.__class__.__name__

    def sendline(self, a):
        self._fp.write(a); self._fp.write("\n")
        self._fp.flush()
        return self._pexp.sendline(a)

    def expect(self, a, timeout=None):
        return self._pexp.expect(a,timeout=timeout)

    def isalive(self):
        return self._pexp.isalive()

    def sendcontrol(self, a):
        return self._pexp.sendcontrol(a)

    def set_before(self, value):
        self._pexp.before = value
    def get_before(self):
        return self._pexp.before
    before = property(get_before, set_before)

    def set_after(self, value):
        self._pexp.after = value
    def get_after(self):
        return self._pexp.after
    after = property(get_after, set_after)

    def read_nonblocking(self, a, timeout=None):
        return self._pexp.read_nonblocking(a,timeout=timeout)

# example config_connect
#config_connect_1 = {
#    'serial': '/dev/ttyUSB0', 'baud': 115200,
#    'ipaddr': 'localhost', 'port': 6001,
#    "virsh_url": "qemu+ssh://username@192.168.1.105/system", "virsh_name": "openwrt-test",
#}
def factory_pexpect(config_connect, output):
    pexp = None
    if ('ipaddr' in config_connect) and (config_connect['ipaddr']) and (not (config_connect['ipaddr'].strip() == '')):
        L.info("telnet to '{0}:{1}':".format(config_connect['ipaddr'], config_connect['port']))
        pexp = pexpect.spawn("telnet " + config_connect['ipaddr'].strip() + " " + str(config_connect['port']) , timeout=600)

    elif ('serial' in config_connect) and (config_connect['serial']) and (not (config_connect['serial'].strip() == '')):
        L.info("use serial port '{0}' and baud '{1}':".format(config_connect['serial'], config_connect['baud']))
        pexp = SerialSpawn(config_connect['serial'], config_connect['baud'], timeout=600)
        assert(pexp.isalive())

    elif ('virsh_name' in config_connect):
        cmd = "virsh"
        url = None
        if 'virsh_url' in config_connect:
            url = config_connect['virsh_url'].strip()
        if url:
            cmd += f" -c {url}"
        cmd += f" console {config_connect['virsh_name'].strip()}"
        L.debug(f"CMD={cmd}")
        pexp = pexpect.spawn(cmd, timeout=600)
        pexp.sendline("\r\n")
        ret = pexp.expect(['Escape character', 'failed to connect to the hypervisor'])
        if (ret != 0):
            L.error("unable to connect to virsh")
            return None

    else:
        L.error("unable to start the device: " + config_connect['name'])
        return None
    #elif config_connect['rest'] and (not (config_connect['rest'].strip() == '')):

    pexp.logfile = output

    assert(pexp.isalive())

    return PexpectWrapper(pexp, config_connect['content_file'].strip())

################################################################################
class StdoutWrapper(io.TextIOWrapper):
    def write(self, string):
        try:
            if isinstance(string, bytes):
                string = string.decode(self.encoding)
            super().write(string)
        except:
            pass

# use to run config function
class ConfigDevice():
    stdout_wrapper = StdoutWrapper(sys.stdout.buffer, encoding='utf-8', write_through=True)

    def __init__(self, config_device, config_connect):
        self.device = factory_device(config_device)
        assert (isinstance(self.device, Switch))
        self.device.pexp = factory_pexpect(config_connect, self.stdout_wrapper)

    def __del__(self):
        #self.device.pexp.close()
        self.stdout_wrapper.close()
        #sys.stdout = sys.stdout.detach()

    def _show_info(self):
        L.info("Driver: '{0}'".format(str(self.device)))
        L.info("Board: '{0}'".format(self.device.get_board()))
        L.info("Model: '{0}'".format(self.device.get_model_name()))
        L.info("Version: '{0}'".format(self.device.get_version()))
        L.info("Hostname: '{0}'".format(self.device.get_hostname()))
        from parseclock import getstr_clock
        L.info("Device Time: '{0}'".format(getstr_clock(self.device.get_clock())))
        return True

    def show_info(self):
        if not self._show_info():
            L.error("ConfigDevice::show_info _show_info error")
            return False
        #L.debug("ConfigDevice::show_info done")
        return True

    def _reset(self, config_reset):
        port_map = config_reset['arg_port_map']
        L.debug("ConfigDevice::_reset device reset_config ...")
        self.device.reset_config(port_map)

        if ('admin_password' in config_reset):
            L.info("ConfigOpenwrt::reset setup root pw")
            self.device.set_root_passwd(config_reset['admin_password'])

        return True

    def reset(self, config_reset):
        if not self._reset(config_reset):
            L.error("ConfigDevice::reset _reset error")
            return False
        L.debug("ConfigDevice::reset device save_config ...")
        self.device.save_config()
        L.debug("ConfigDevice::reset done")
        return True

    def reboot(self, wait_network=True):
        self.device.reboot(wait_network)
        L.debug("ConfigDevice::reboot done")
        return True

    # setup the device config with the specified interface/vlan layout
    #example of config_layout:
    #config_layout_1 = {
    #    'arg_port_map': port_map_ciscogns3, # the external port names to internal port num/name
    #    'arg_vlan_set': vlan_set_netlab, # the set of all vlan
    #    'arg_port_list': switch_hw_ports_ow_netlab, # the ports need to be configured
    #    'arg_vlan_list': switch_hw_vlans_ow_netlab, # the vlan id for each port to be configured
    #
    #    'arg_interface_config': interface_config_netlab, # the openwrt interface config
    #    'arg_local_addr': "192.168.5.0/24", # the ip blocks for LAN
    #}
    def _set_layout(self, config_layout):

        L.info("ConfigDevice::_set_layout set hostname")
        self.device.set_hostname(config_layout['arg_hostname'])

        # get all of the VLAN IDs from the interface config
        interface_config_homemain=config_layout["arg_interface_config"]
        vlan_set_homemain = {1,2}.union({ interface_config_homemain[i][0] for i in interface_config_homemain })
        L.debug("vlan_set_homemain=" + str(vlan_set_homemain))

        if 'arg_port_vlan' in config_layout:
            port_vlan = config_layout['arg_port_vlan']
            [port_list, vlan_list] = port_vlan_to_lists(port_vlan)
        elif ('arg_port_list' in config_layout) and ('arg_vlan_list' in config_layout):
            vlan_list = config_layout['arg_vlan_list']
            port_list = config_layout['arg_port_list']
        else:
            L.error('not found config of port map')
            return False

        if not self.device.set_vlans(config_layout['arg_port_map'], port_list, vlan_list, vlan_set_homemain, interface_config = interface_config_homemain):
            return False
        return True

    def set_layout(self, config_layout):
        if not self._set_layout(config_layout):
            L.error("ConfigDevice::set_layout _set_layout error")
            return False
        self.device.save_config()
        L.debug("ConfigDevice::set_layout done")
        return True

class ConfigOpenwrt(ConfigDevice):
    def __init__(self, config_device, config_connect):
        super().__init__(config_device, config_connect)

    def _show_info(self):
        L.debug("ConfigOpenwrt::_show_info super()._show_info ...")
        L.info("swconfig: '{0}'".format(self.device.get_swconfig()))
        #self.device.show_network()
        if not super()._show_info():
            L.error("ConfigOpenwrt::_show_info super()._show_info error")
            return False
        return True

    def _reset(self, config_reset):

        if not super()._reset(config_reset):
            L.error("ConfigDevice::_reset super()._reset error")
            return False

        L.info("ConfigOpenwrt::reset set timezone")
        self.device.set_timezone()

        self.device.save_config() # save config before update the softwares

        L.info("ConfigOpenwrt::reset update softwares")
        extra = [ "luci-ssl", "uhttpd", "ip-full", "ip-bridge", "gawk" ]
        if "extra_packets" in config_reset:
            extra = config_reset["extra_packets"]
        if not self.device.update_softwares(extra):
            L.error("ConfigOpenwrt::reset error in update_softwares")
            return False

        L.info("ConfigOpenwrt::reset done")
        return True

    # setup a openwrt router, 5 ports
    def _set_layout(self, config_layout):
        if not super()._set_layout(config_layout):
            L.error("ConfigOpenwrt::_set_layout error in super()._set_layout")
            return False

        assert (isinstance(self.device, OpenwrtSwitch))

        self.device.change_to_https()

        port_map = config_layout['arg_port_map']

        if 'arg_port_vlan' in config_layout:
            port_vlan = config_layout['arg_port_vlan']
            port_list = sorted(port_vlan)
            vlan_list = [port_vlan[i] for i in port_list]
        else:
            vlan_list = config_layout['arg_vlan_list']
            port_map = config_layout['arg_port_map']

        L.info("ConfigOpenwrt::_set_layout set interfaces")
        ifname_gen=None
        if not self.device.has_hw_switch:
            ifname_gen = VlanPortGenerator(port_map, port_list, vlan_list)
        L.debug(f"ConfigOpenwrt::_set_layout ifname_gen={ifname_gen}")
        self.device.setup_br_trunk(port_list, vlan_list)
        if not self.device.set_interfaces(ipaddr_lan=config_layout['arg_local_addr'], interface_config=config_layout['arg_interface_config'], port_map=port_map, ifname_gen=ifname_gen):
            L.error("ConfigOpenwrt::_set_layout error in set_interfaces 3")
            return False

        L.info("ConfigOpenwrt::_set_layout done")
        return True

class ConfigOpenwrtHomemain(ConfigOpenwrt):
    def __init__(self, config_device, config_connect):
        super().__init__(config_device, config_connect)

    # setup a openwrt router, 5 ports
    def _set_layout(self, config_layout):
        if not super()._set_layout(config_layout):
            L.error("ConfigOpenwrtHomemain::_set_layout error in super()._set_layout")
            return False

        if "external_tftp" in config_layout:
            ip = config_layout["external_tftp"].strip()
            if ip:
                L.info("ConfigOpenwrtHomemain::_set_layout set tftp")
                self.device.setup_tftp_external(addr_tftpd = ip)

        if "arg_app_zone" in config_layout:
            for i in config_layout["arg_app_zone"]:
                L.info(f"ConfigOpenwrtHomemain::set_access_server set {i['name']}")
                self.device.setup_access_server(i)

        if "dns_server" in config_layout:
            for i in config_layout["dns_server"]:
                L.info(f"ConfigOpenwrtHomemain::setup_dns_server set {i['name']}")
                self.device.setup_dns_server(i)

        if "wan_port" in config_layout:
            for i in config_layout["wan_port"]:
                L.info(f"ConfigOpenwrtHomemain::setup_wan_port set {i['name']}")
                self.device.setup_wan_port(i)

        L.info("ConfigOpenwrtHomemain::_set_layout done")
        return True


def factory_config_device(config_device):
    device = None
    if config_device['driver'] == 'openwrtuci':
        L.debug('return ConfigOpenwrtHomemain')
        device = ConfigOpenwrtHomemain(config_device, config_device)
    else:
        device = ConfigDevice(config_device, config_device)

    return device


def setup_network_equipment(configs, reset=True, command="layout"):

    #import json
    #L.debug("use config:\n" + json.dumps(configs, indent=4))

    rt1 = factory_config_device(configs)

    rt1.show_info()
    if command == "info":
        L.info("get info completed")
        return True
    if command == "reset":
        reset = True

    if reset:
        L.info("reset ...")
        ret = rt1.reset(configs)
        if not ret:
            L.error("reset error")
            return False

    if command == "reset":
        L.info("reset completed")
        return True

    ret = rt1.set_layout(configs)
    if not ret:
        L.error("set_layout error")
        return False

    rt1.reboot(wait_network=False)
    L.info("layout completed")
    return True

################################################################################
if __name__ == '__main__':
    import unittest
    class myTest(unittest.TestCase):
        def setUp(self):
            pass
        def tearDown(self):
            pass

        def test_factory_device(self):
            device = factory_device({
                'name': 'Cisco-netlab-gns3',
                'driver': 'ciscoios',
                #'arg_has_hw_switch': True, # ignored
            })
            self.assertEqual(isinstance(device, Switch), True)
            self.assertEqual(isinstance(device, CiscoSwitch), True)
            self.assertEqual(device.has_hw_switch, False)

            device = factory_device({
                'name': 'Dell-netlab-pc5324', # Dell PowerConnect 5324
                'driver': 'dellpc',
                #'arg_has_hw_switch': True, # ignored
            })
            self.assertEqual(isinstance(device, Switch), True)
            self.assertEqual(isinstance(device, DellSwitch), True)
            self.assertEqual(device.has_hw_switch, False)

            device = factory_device({
                'name': 'OpenWrt-netlab-tplinkac1200',
                'driver': 'openwrtuci',
                'arg_has_hw_switch': True,
            })
            self.assertEqual(isinstance(device, Switch), True)
            self.assertEqual(isinstance(device, OpenwrtSwitch), True)
            self.assertEqual(device.has_hw_switch, True)


        def test_factory_pexpect(self):
            pass

        def test_constant1(self):
            self.assertEqual(vlan_set_homemain, {5,6,10,20,30,40,50,60,70,80,90,100,110,120})
            self.assertEqual(vlan_set_netlab, {6,20,60,90,100,110})
            self.assertEqual(switch_hw_ports_dellpc5324, [ 'g1', 'g2', 'g3', 'g4', 'g5', 'g6', 'g7', 'g8', 'g9', 'g10', 'g11', 'g12', 'g13', 'g14', 'g15', 'g16', 'g17', 'g18', 'g19', 'g20', 'g21', 'g22', 'g23', 'g24' ])
            self.assertEqual(switch_hw_vlans_dellpc5324, [
                100,100,100,100,100, 100,100,100,100,100, 100,100,100,100,100, 100,
                1,2,5,6, 0,0,0,0
                ])

    #unittest.main()

    # tested:
    #setup_gns3_rt_openwrt_netlab()
    #setup_gns3_rt_openwrt_homemain()
    #setup_device_rt_tplink_ac1200_homemain(change_ip=True)
    #setup_device_rt_tplink_ac1200_netlab()
    #setup_gns3_sw_cisco()
    #setup_device_sw_cisco()
    #setup_device_sw_dell()
    #setup_device_sw_hpj9727a()

    #setup_network_netlabtest()
    #setup_network_gns3_homemain()
    #setup_network_homemain()


################################################################################
# main

parser=argparse.ArgumentParser(description='setup switch network.')
parser.add_argument('-l', '--logfile', type=str, dest='fnlog', default="/dev/stderr", help='the file to output the log')
parser.add_argument('-o', '--outputfile', type=str, dest='fnout', default="/dev/stderr", help='the file save the setup contents')
parser.add_argument('-j', '--json', type=str, dest='json', default=None, help="the JSON config file")
parser.add_argument('-s', '--noreset', action='store_true', default=False, help='reset the router to factory mode')
parser.add_argument('-t', '--type', type=str, dest='type', default="openwrtuci", help='the device driver type')
parser.add_argument('-d', '--debug', action='store_true', default=False, help='show debug messages')
parser.add_argument('-v', '--version', action='store_true', default=False, help='show version')
parser.add_argument('c', type=str, help='The command, such as "info", "reset", "layout"; default is "layout"')
args = parser.parse_args()

log_level = logging.INFO
if args.debug:
    log_level = logging.DEBUG
L.setLevel(log_level)

if args.version:
    L.info("version: " + __version__)
    exit(0)

if args.fnlog == "/dev/stderr":
    L.info ("output log to standard error")
else:
    mylog.add_file_logger('switch', args.fnlog, log_level)

conf={"driver": args.type, "content_file": args.fnout }
L.debug("args.json=" + str(args.json))
if args.json:
    with open(args.json, "r") as file:
        conf_update = pyjson5.load(file)
        # update the config conf with conf_update
        conf.update(conf_update)

#L.debug("conf=" + str(conf))

setup_network_equipment(conf, reset=not args.noreset, command=args.c)



