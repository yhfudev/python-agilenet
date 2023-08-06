#!/usr/bin/env python3
# encoding: utf8
# -*- coding: utf-8 -*-
#
# The config functions for OpenWrt uci
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
import time

import re
import pexpect

from switchdevice import Switch, port_vlan_to_lists, pexpect_clean_buffer
from parseclock import parse_clock_openwrt
from configutil import get_network_addr, interfaces_has_subnet_ips

try:
    FileNotFoundError # python 3
except NameError:
    FileNotFoundError = IOError # python 2

PROGRAM_PREFIX = os.path.basename(__file__).split('.')[0]

import logging
L = logging.getLogger('switch')

################################################################################
def parse_model_line(str_model):
    search_item = re.search('get_model_begin[\s\n]+(.*)', str_model)
    #search_item = re.search('get_model_begin=(.*)', str_model)
    #L.info("1 search='{0}'".format(search_item))
    #L.info("1 search(0)='{0}'".format(search_item.group(0)))
    #L.info("1 search(1)='{0}'".format(search_item.group(1)))
    if not search_item:
        return str_model.strip()
    return search_item.group(1).strip()

def parse_board_line(str_board):
    search_item = re.search('get_board_begin[\s\n]+(.*)', str_board)
    #search_item = re.search('get_board_begin=(.*)', str_board)
    #L.info("1 search='{0}'".format(search_item))
    #L.info("1 search(0)='{0}'".format(search_item.group(0)))
    #L.info("1 search(1)='{0}'".format(search_item.group(1)))
    if not search_item:
        return str_board.strip()
    return search_item.group(1).strip()

def parse_version(str_version):
    # cat /etc/openwrt_release | grep DISTRIB_RELEASE | awk -F= {'print $2'}
    # DISTRIB_RELEASE='SNAPSHOT'
    # DISTRIB_REVISION='r15475-c625c821d1'
    # cat /etc/os-release | grep "VERSION=" | awk -F= {'print $2'}
    # VERSION="22.03.0-rc6"
    search_item = re.search("DISTRIB_RELEASE='(.*)'", str_version)
    #L.info("2 search='{0}'".format(search_item))
    #L.info("2 search(0)='{0}'".format(search_item.group(0)))
    #L.info("2 search(1)='{0}'".format(search_item.group(1)))
    ret = search_item.group(1).strip()
    if ret == 'SNAPSHOT':
        search_item = re.search("DISTRIB_REVISION='(.*)'", str_version)
        #L.info("2.2 search='{0}'".format(search_item))
        #L.info("2.2 search(0)='{0}'".format(search_item.group(0)))
        #L.info("2.2 search(1)='{0}'".format(search_item.group(1)))
        ret = search_item.group(1).strip()
    #L.info("version='{0}'".format(ret))
    return ret

def parse_target(str_target):
    # cat /etc/openwrt_release | grep "DISTRIB_TARGET=" | awk -F= {'print $2'}
    # DISTRIB_TARGET='ath79/generic'
    # cat /etc/os-release | grep "OPENWRT_BOARD=" | awk -F= {'print $2'}
    # OPENWRT_BOARD="ath79/generic"
    search_item = re.search("DISTRIB_TARGET='(.*)'", str_target)
    #L.info("2 search='{0}'".format(search_item))
    #L.info("2 search(0)='{0}'".format(search_item.group(0)))
    #L.info("2 search(1)='{0}'".format(search_item.group(1)))
    ret = search_item.group(1).strip()
    #L.info("target='{0}'".format(ret))
    return ret

def parse_hostname(str_output):
    search_item = re.search("='(.*)'", str_output)
    if not search_item:
        return None
    return search_item.group(1).strip()

# example:
#   swconfig list
#   Found: switch0 - rtl8367
#   /bin/ash: swconfig: not found
"""# sample:
get_swconfig_begin
Found: switch0 - rtl8367
get_swconfig_end
"""
def parse_swconfig_line(str_model):
    search_item = re.search('get_swconfig_begin[\s\n]+(.*)', str_model)
    if not search_item:
        search_item = re.search('(Found:.*)', str_model)
    #L.debug("parse_swconfig_line='{0}'".format(search_item))
    #if search_item:
    #    L.debug("parse_swconfig_line(0)='{0}'".format(search_item.group(0)))
    #    L.debug("parse_swconfig_line(1)='{0}'".format(search_item.group(1)))
    str_line = None
    if not search_item:
        str_line = str_model.strip()
    else:
        str_line = search_item.group(1).strip()
    #L.debug("parse_swconfig_line str_line='{0}'".format(str_line))

    #items = str(str_line).split()
    #val = items[len(items)-1].split("\\")[0]
    #L.debug("the device: " + val)
    if str_line:
        items = str(str_line).split()
        if items[0] == "Found:":
            return [ items[1], items[3] ]
    return None

#     --vlan
#	Attribute 1 (int): vid (VLAN ID (0-4094))
def parse_swconfig_support_vid_line(str_line):
    search_item = re.search('\(int\): vid ', str_line)
    if search_item:
        return True
    return False

def parse_swconfig_support_vlan4k_line(str_line):
    search_item = re.search('enable_vlan4k', str_line)
    if search_item:
        return True
    return False

################################################################################

# get the config for the interface ip/mask
#cmd_intf += getconf_set_network(ipnet, 'lan')
def getconf_set_network(ipnet, interface):
    lst = list(ipnet.hosts())
    cmd_intf = f"set network.{interface}.proto='static'\n"
    cmd_intf += f"set network.{interface}.ipaddr='{str(lst[0])}'\n"
    cmd_intf += f"set network.{interface}.netmask='{str(ipnet.netmask)}'\n"
    return cmd_intf

# set the start value of the last number of IP
def getconf_set_ipv4_24_range(ipnet, interface):
    cmd_intf = ""
    if ipnet and (24 <= ipnet.prefixlen) and (ipnet.prefixlen < 32):
        lst = list(ipnet.hosts())
        start_num = str(lst[0]).split('.')[3]
        #end_num = str(lst[len(lst)-1]).split('.')[3]
        start_num = int(start_num) + 1
        cmd_intf += f"set dhcp.{interface}.start='{start_num}'\n"
        cmd_intf += f"set dhcp.{interface}.limit='{ipnet.num_addresses - 2}'\n"
    return cmd_intf

# For DSA, setup a new bridge device for the used ehternet ports
def _getconf_trunk_bridge_device(port_map, port_list, trunk_bridge_device_name, has_subnet_ips=False):
    cmd_intf = ""

    cmd_intf += """add network device
set network.@device[-1].name='{0}'
set network.@device[-1].type='bridge'
""".format(trunk_bridge_device_name)
    set1 = { i for i in port_list }
    #L.debug(f"set0={set1}")
    set1.discard('CPU')
    set1.discard('CPU2')
    if has_subnet_ips: set1.discard('WAN')
    #L.debug(f"set1={set1}")
    dev1 = { port_map[i][0] for i in set1 }
    #L.debug(f"dev1={dev1}")
    device_list = sorted(dev1)
    L.debug(f"device_list={device_list}")
    L.debug(f"port_list={port_list}")
    for ifname in device_list:
        if ifname:
            cmd_intf += f"add_list network.@device[-1].ports={ifname}\n"
        else:
            L.warning("error in ifname: {ifname}")
    return cmd_intf

# trunk_bridge_device_name: the br_trunk bridge name, it can be either 'br-lan' if the LAN connected to a physical ethernet port, or 'br_trunk' for the sub-network VLANs only.
# has_subnet_ips: True if has subnet IPs, it's a main router, and need the 'wan' separated for DSA.
def getconf_vlan_dsa(port_map, port_list, vlan_list, vlan_set, trunk_bridge_device_name, has_subnet_ips=False):
    cmd_intf = "# bridge-vlan\n"

    L.debug("getconf_vlan_dsa() arg has_subnet_ips={}".format(has_subnet_ips))
    #print(f"port_list={port_list}")
    #print(f"vlan_list={vlan_list}")
    #vlan_set1 = vlan_set.union({ i for i in vlan_list })
    vlan_set1 = vlan_set
    for i in vlan_list:
        if isinstance(i, list):
            vlan_set1 = vlan_set1.union(set(i))
        else:
            vlan_set1 = vlan_set1.union({i})
    vlan_set1.discard(0)
    if trunk_bridge_device_name != 'br-lan': vlan_set1.discard(1) # LAN
    if not has_subnet_ips: vlan_set1.discard(2) # WAN
    vlan_list_set = list(vlan_set1)
    vlan_list_set.sort()

    #cmd_intf += "commit\nEOF\n\nuci batch << EOF\n"
    cmd_intf += "\n"

    for vlan_num in vlan_list_set:
        L.debug(f"setup bridge-vlan for VLAN '{vlan_num}':")

        cmd_intf += """add network bridge-vlan
set network.@bridge-vlan[-1].device='{0}'
set network.@bridge-vlan[-1].vlan='{1}'
""".format(trunk_bridge_device_name, vlan_num)
        # get all of the if for vlan
        for j in range(0,len(vlan_list)):
            if port_list[j] == 'CPU': continue
            if port_list[j] == 'CPU2': continue
            if has_subnet_ips and port_list[j] == 'WAN': continue

            #L.debug(f"j={j}/len={len(vlan_list)}")
            #L.debug(f"j={j}/port_list[j]={port_list[j]}")
            #L.debug(f"j={j}/port_map[port_list[j]]={port_map[port_list[j]]}")
            #L.debug(f"len(port_list)={len(port_list)}; len(vlan_list)={len(vlan_list)}; j={j}")
            vlan1 = vlan_list[j]
            if not isinstance(vlan1, list):
                vlan1 = [ vlan_list[j] ]
            for v in vlan1:
                if v == vlan_num:
                    # untagged
                    cmd_intf += f"add_list network.@bridge-vlan[-1].ports='{port_map[port_list[j]][0]}:u*'\n"
                elif (v == 0) and (vlan_num in vlan_set):
                    # tagged
                    cmd_intf += f"add_list network.@bridge-vlan[-1].ports='{port_map[port_list[j]][0]}:t'\n"
        cmd_intf += "\n"

    return cmd_intf

## setup a default VLAN for HW switch
#  @param port_map
#  @param switch_name
def getconf_default_vlan_swconfig(port_map, switch_name="switch0", support_vlan4k=False):

    cmd_intf="uci batch << EOF"

    cmd_intf += """
# Default VLANs
add network switch
set network.@switch[-1].name={0}
set network.@switch[-1].reset=1
set network.@switch[-1].enable_vlan=1
""".format(switch_name)

    if support_vlan4k:
        cmd_intf += "set network.@switch[-1].enable_vlan4k=1\n"

    cmd_intf += """commit
EOF
"""

    port_list = [ i for i in port_map]
    vlan_list = [ 1 for i in range(0,len(port_list)) ]
    for i in range(0,len(port_list)):
        if port_list[i] == 'CPU':
            vlan_list[i] = 0
        elif port_list[i] == 'WAN':
            vlan_list[i] = 2
    L.info("port_map = {0}".format(port_map))
    L.info("port_list = {0}".format(port_list))
    L.info("vlan_list = {0}".format(vlan_list))
    cmd_intf += getconf_vlans_swconfig(port_map, port_list, vlan_list, {1,2}, switch_name=switch_name)

    #L.info("getconf_default_vlan_swconfig cmd=" + cmd_intf)
    return cmd_intf


## setup a default LAN and WAN
#  @param cb_vlan_ifname An alternate ifname callback function.
#  @param dev_lan The ethernet card name for LAN, such as 'eth1'
#  @param dev_wan The ethernet card name for WAN, such as 'eth0'
def getconf_default_network(cb_vlan_ifname=None, dev_lan='eth0', dev_wan='eth0', dns_resolv_file='/tmp/resolv.conf.d/resolv.conf.auto'):

    # lan
    if not (dev_lan == ''):
        i = 'lan'
        ipaddr_lan = "192.168.1.0/24"
        vlan = 1
        if None == cb_vlan_ifname:
            ifname = "{0}.{1}".format(dev_lan, vlan)
        else:
            ifname = "{0}".format(cb_vlan_ifname(vlan))

        cmd_intf="uci batch << EOF\n"

        cmd_intf += """
# Default Network
set network.globals='globals'
set network.globals.ula_prefix='fd35:f963:a3ba::/48'
"""

        cmd_intf += """
# loopback
set network.loopback='interface'
set network.loopback.ifname='lo'
set network.loopback.proto='static'
set network.loopback.ipaddr='127.0.0.1'
set network.loopback.netmask='255.0.0.0'
"""
#ipnet=get_network_addr('127.0.0.0/8')
#cmd_intf += getconf_set_network(ipnet, 'loopback')


        cmd_intf += """
# Interface {0} on ifname {1}
set network.{0}='interface'
set network.{0}.type='bridge'
set network.{0}.ifname='{1}'
set network.{0}.ip6assign='60'
""".format(i, ifname)

        ipnet = get_network_addr(ipaddr_lan)
        if ipnet == None:
            L.warning("2 unable to get network address for '{0}'".format(ipaddr_lan))
        else:
            cmd_intf += getconf_set_network(ipnet, i)

        cmd_intf += """
set dhcp.{0}='dhcp'
set dhcp.{0}.interface='{0}'
set dhcp.{0}.leasetime='12h'
set dhcp.{0}.start='100'
set dhcp.{0}.limit='150'
set dhcp.{0}.ra_management='1'
set dhcp.{0}.dhcpv4='server'
set dhcp.{0}.dhcpv6='server'
set dhcp.{0}.ra='server'
""".format(i, ifname)

    i = 'wan'
    vlan = 2
    if None == cb_vlan_ifname:
        ifname = "{0}.{1}".format(dev_wan, vlan)
    else:
        ifname = "{0}".format(cb_vlan_ifname(vlan))

    cmd_intf += """
# Interface {0} on ifname {1}
set network.{0}='interface'
set network.{0}.type='bridge'
set network.{0}.ifname='{1}'
set network.{0}.proto='dhcp'
""".format(i, ifname)

    cmd_intf += """
# Configure DNS provider
set network.wan.peerdns="1"
#set network.wan.dns="8.8.8.8 8.8.4.4"
set network.wan6.peerdns="1"
#set network.wan6.dns="2001:4860:4860::8888 2001:4860:4860::8844"
"""

    i = 'wan6'
    cmd_intf += """
set network.{0}='interface'
set network.{0}.type='bridge'
set network.{0}.ifname='{1}'
set network.{0}.proto='dhcpv6'
""".format(i, ifname)

    cmd_intf += """
set dhcp.{0}='dhcp'
set dhcp.{0}.interface='{0}'
set dhcp.{0}.ignore='1'
""".format('wan')

    cmd_intf += """
add dhcp dnsmasq
set dhcp.@dnsmasq[0]=dnsmasq
set dhcp.@dnsmasq[0].domainneeded='1'
set dhcp.@dnsmasq[0].boguspriv='1'
set dhcp.@dnsmasq[0].filterwin2k='0'
set dhcp.@dnsmasq[0].localise_queries='1'
set dhcp.@dnsmasq[0].rebind_protection='1'
set dhcp.@dnsmasq[0].rebind_localhost='1'
set dhcp.@dnsmasq[0].local='/lan/'
set dhcp.@dnsmasq[0].domain='lan'
set dhcp.@dnsmasq[0].expandhosts='1'
set dhcp.@dnsmasq[0].nonegcache='0'
set dhcp.@dnsmasq[0].authoritative='1'
set dhcp.@dnsmasq[0].readethers='1'
set dhcp.@dnsmasq[0].leasefile='/tmp/dhcp.leases'
set dhcp.@dnsmasq[0].nonwildcard='1'
set dhcp.@dnsmasq[0].localservice='1'
# set default DNS
del dhcp.@dnsmasq[0].server
add_list dhcp.@dnsmasq[0].server='8.8.8.8'
add_list dhcp.@dnsmasq[0].server='8.8.4.4'

set dhcp.odhcpd='odhcpd'
set dhcp.odhcpd.maindhcp='0'
set dhcp.odhcpd.leasefile='/tmp/hosts/odhcpd'
set dhcp.odhcpd.leasetrigger='/usr/sbin/odhcpd-update'
set dhcp.odhcpd.loglevel='4'

add firewall defaults
set firewall.@defaults[0].syn_flood='1'
set firewall.@defaults[0].input='ACCEPT'
set firewall.@defaults[0].output='ACCEPT'
set firewall.@defaults[0].forward='REJECT'
#set firewall.@defaults[0].disable_ipv6='1'

add firewall zone
set firewall.@zone[-1].name=lan
set firewall.@zone[-1].network='lan'
set firewall.@zone[-1].input=ACCEPT
set firewall.@zone[-1].output=ACCEPT
set firewall.@zone[-1].forward=ACCEPT

add firewall zone
set firewall.@zone[-1].name=wan
set firewall.@zone[-1].network='wan wan6'
set firewall.@zone[-1].input=REJECT
set firewall.@zone[-1].output=ACCEPT
set firewall.@zone[-1].forward=REJECT
set firewall.@zone[-1].masq=1
set firewall.@zone[-1].mtu_fix=1

add firewall forwarding
set firewall.@forwarding[-1].src=lan
set firewall.@forwarding[-1].dest=wan

add firewall rule
set firewall.@rule[-1].name='Allow-DHCP-Renew'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='udp'
set firewall.@rule[-1].dest_port='68'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv4'

add firewall rule
set firewall.@rule[-1].name='Allow-Ping'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='icmp'
set firewall.@rule[-1].icmp_type='echo-request'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv4'

add firewall rule
set firewall.@rule[-1].name='Allow-IGMP'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='igmp'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv4'

add firewall rule
set firewall.@rule[-1].name='Allow-DHCPv6'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='udp'
set firewall.@rule[-1].src_ip='fc00::/6'
set firewall.@rule[-1].dest_ip='fc00::/6'
set firewall.@rule[-1].dest_port='546'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-MLD'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='icmp'
set firewall.@rule[-1].src_ip='fe80::/10'
#delete firewall.@rule[-1].icmp_type
add_list firewall.@rule[-1].icmp_type='130/0'
add_list firewall.@rule[-1].icmp_type='131/0'
add_list firewall.@rule[-1].icmp_type='132/0'
add_list firewall.@rule[-1].icmp_type='143/0'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-ICMPv6-Input'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='icmp'
#delete firewall.@rule[-1].icmp_type
add_list firewall.@rule[-1].icmp_type='echo-request'
add_list firewall.@rule[-1].icmp_type='echo-reply'
add_list firewall.@rule[-1].icmp_type='destination-unreachable'
add_list firewall.@rule[-1].icmp_type='packet-too-big'
add_list firewall.@rule[-1].icmp_type='time-exceeded'
add_list firewall.@rule[-1].icmp_type='bad-header'
add_list firewall.@rule[-1].icmp_type='unknown-header-type'
add_list firewall.@rule[-1].icmp_type='router-solicitation'
add_list firewall.@rule[-1].icmp_type='neighbour-solicitation'
add_list firewall.@rule[-1].icmp_type='router-advertisement'
add_list firewall.@rule[-1].icmp_type='neighbour-advertisement'
set firewall.@rule[-1].limit='1000/sec'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-ICMPv6-Forward'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].dest='*'
set firewall.@rule[-1].proto='icmp'
#delete firewall.@rule[-1].icmp_type
add_list firewall.@rule[-1].icmp_type='echo-request'
add_list firewall.@rule[-1].icmp_type='echo-reply'
add_list firewall.@rule[-1].icmp_type='destination-unreachable'
add_list firewall.@rule[-1].icmp_type='packet-too-big'
add_list firewall.@rule[-1].icmp_type='time-exceeded'
add_list firewall.@rule[-1].icmp_type='bad-header'
add_list firewall.@rule[-1].icmp_type='unknown-header-type'
set firewall.@rule[-1].limit='1000/sec'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-IPSec-ESP'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].dest='lan'
set firewall.@rule[-1].proto='esp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='Allow-ISAKMP'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].dest='lan'
set firewall.@rule[-1].dest_port='500'
set firewall.@rule[-1].proto='udp'
set firewall.@rule[-1].target='ACCEPT'

add firewall include
set firewall.@include[-1].path='/etc/firewall.user'

add system system
set system.@system[-1].hostname='OpenWrt'
set system.@system[-1].timezone='UTC'
set system.@system[-1].ttylogin='0'
set system.@system[-1].log_size='64'
set system.@system[-1].urandom_seed='0'

set system.ntp='timeserver'
set system.ntp.enabled='1'
set system.ntp.enable_server='0'
#delete system.ntp.server
add_list system.ntp.server='0.openwrt.pool.ntp.org'
add_list system.ntp.server='1.openwrt.pool.ntp.org'
add_list system.ntp.server='2.openwrt.pool.ntp.org'
add_list system.ntp.server='3.openwrt.pool.ntp.org'
"""

    # option resolvfile '/tmp/resolv.conf.d/resolv.conf.auto'
    cmd_intf += f"set dhcp.@dnsmasq[0].resolvfile='{dns_resolv_file}'\n"

    cmd_intf += """commit
EOF
"""
    #L.info("getconf_default_net cmd=" + cmd_intf)
    return cmd_intf


def get_hw_wifi_number(str_msg):
    return len(re.findall(r'phy\#[0-9]+', str_msg))

## setup interfaces and its firewall rules
#  @param hostname The hostname of the device
#  @param ipaddr_lan The network/bit, such as ipaddr_lan="192.168.111.0/24"
#  @param interface_config
#    example:
#    interface_config_homemain = {
#      # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
#      "coredata": [  10, "10.1.1.000/29", "", "", []],
#    }
#  @param port_map The port name to switch port/device map.
#    example:
#    port_map_mydev = {
#      "CPU": [ 0, "eth0" ],
#    }
#  @param cb_vlan_ifname An alternate ifname callback function.
#  @param is_dsa True if the board support Linux DSA
#  @param trunk_bridge_device_name the bridge for DSA interfaces
#  @return a list of config command strings
def getconf_list_interfaces(hostname, ipaddr_lan, interface_config, port_map, cb_vlan_ifname=None, num_wifi=0, is_dsa=False, create_wan=False, has_subnet_ips=True, default_passwd="", trunk_bridge_device_name = 'br-lan'):
    # TODO: new DSA bridge-vlan

    #L.info("getconf_interfaces with cb = {0}".format(cb_vlan_ifname))
    ret_conf_list = []

    cmd_intf=""
    if num_wifi > 0:
        cmd_intf += """
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1
"""

        # setup a wifi for lan, the hostname as wifi name, and the key 'abcd1234' as the key
        ssid_lan = hostname
        key_lan = default_passwd
        if not key_lan:
            L.error("not set password.")
            key_lan = "password"
            L.error("the WiFi '{0}' access password was set to default '{1}'".format(ssid_lan, key_lan))
        cmd_intf += """
set wireless.@wifi-iface[-1].disabled=0
set wireless.@wifi-iface[-1].mode='ap'
set wireless.@wifi-iface[-1].encryption='psk2+ccmp'
set wireless.@wifi-iface[-1].disassoc_low_ack='0'
set wireless.@wifi-iface[-1].wps_pushbutton='0'
set wireless.@wifi-iface[-1].network='{1}'
set wireless.@wifi-iface[-1].ssid='{2}'
set wireless.@wifi-iface[-1].key='{3}'
set wireless.@wifi-iface[-1].ieee80211r='1'
set wireless.@wifi-iface[-1].ft_over_ds='0'
set wireless.@wifi-iface[-1].ft_psk_generate_local='1'
set wireless.@wifi-iface[-2].disabled=0
set wireless.@wifi-iface[-2].mode='ap'
set wireless.@wifi-iface[-2].encryption='psk2+ccmp'
set wireless.@wifi-iface[-2].disassoc_low_ack='0'
set wireless.@wifi-iface[-2].wps_pushbutton='0'
set wireless.@wifi-iface[-2].network='{1}'
set wireless.@wifi-iface[-2].ssid='{2}'
set wireless.@wifi-iface[-2].key='{3}'
set wireless.@wifi-iface[-2].ieee80211r='1'
set wireless.@wifi-iface[-2].ft_over_ds='0'
set wireless.@wifi-iface[-2].ft_psk_generate_local='1'
""".format(0, 'lan', ssid_lan, key_lan)

        ret_conf_list.append(cmd_intf); cmd_intf = ""

        # if there's no enough port for LAN, or is for a edge wifi
        if (len(port_map) < 3) or (not has_subnet_ips):
            cmd_intf += """
set wireless.@wifi-device[0].disabled=0
set wireless.@wifi-device[1].disabled=0
"""
        else:
            cmd_intf += """
set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1
"""

    #luci-reload
    #wifi reload

    for i in interface_config:
        L.debug("setup network '{0}':".format(i))

        #if not i == "guest": continue # debug

        cmd_intf += """
set network.{0}='interface'
""".format(i)
        if is_dsa:
            ifname = "{0}.{1}".format(trunk_bridge_device_name, interface_config[i][0]) # LAN for all interface_config
            cmd_intf += """
set network.{0}.type='bridge'
set network.{0}.device='{1}'
""".format(i, ifname)
            # delete network.{0}.ifname
        else:
            if cb_vlan_ifname:
                ifname = "{0}".format(cb_vlan_ifname(interface_config[i][0]))
            else:
                ifname = "{0}.{1}".format(port_map["1"][1], interface_config[i][0]) # LAN for all interface_config

            cmd_intf += """
set network.{0}.type='bridge'
set network.{0}.ifname='{1}'
""".format(i, ifname)

        ipnet = get_network_addr(interface_config[i][1])
        if ipnet == None:
            L.warning("3 unable to get network address for '{0}'".format(interface_config[i][1]))
            cmd_intf += """
set network.{0}.proto='none'
""".format(i)

        else:
            lst = list(ipnet.hosts())

            # TODO: disable the IPv6 of the untrust sub-network
            if not (i == 'untrust'):
                cmd_intf += """
set network.{0}.ip6assign='60'
""".format(i)

            cmd_intf += getconf_set_network(ipnet, i)

            cmd_intf += """
set dhcp.{0}='dhcp'
set dhcp.{0}.interface='{0}'
set dhcp.{0}.leasetime='4h'
set dhcp.{0}.ra_management='1'
set dhcp.{0}.dhcpv4='server'
set dhcp.{0}.dhcpv6='server'
set dhcp.{0}.ra='server'
""".format(i)

            cmd_intf += getconf_set_ipv4_24_range(ipnet, i)

            #if len(interface_config[i][4]) < 1:
                # disable DHCP to set the default router
                #cmd_intf += f"add_list dhcp.{i}.dhcp_option='3'\n"
                # To disable setting the DNS server
                # option dhcp_option '6'

        ret_conf_list.append(cmd_intf); cmd_intf = ""

        if len(interface_config[i][4]):
            cmd_intf += """
add firewall zone
set firewall.@zone[-1].name='fw_{0}'
set firewall.@zone[-1].network='{0}'
set firewall.@zone[-1].input='ACCEPT'
set firewall.@zone[-1].output='ACCEPT'
set firewall.@zone[-1].forward='REJECT'
""".format(i)
            ret_conf_list.append(cmd_intf); cmd_intf = ""

            L.debug("get forward for the zone '{0}'".format(i))
            for j in interface_config[i][4]:
                cmd_intf += """
add firewall forwarding
set firewall.@forwarding[-1].dest='{1}'
set firewall.@forwarding[-1].src='fw_{0}'
""".format(i, j)
        if cmd_intf and (not (cmd_intf == "")):
            ret_conf_list.append(cmd_intf); cmd_intf = ""

        # set wireless.@wifi-iface[-1].name='wifi{0}V{1}'
        # setup wifi
        if num_wifi > 0 and (not interface_config[i][2] == ""):
            for w in range(0,num_wifi):
                cmd_intf += """
set wireless.wifinet{0}{1}='wifi-iface'
set wireless.wifinet{0}{1}.device='radio{0}'
set wireless.wifinet{0}{1}.mode='ap'
set wireless.wifinet{0}{1}.encryption='psk2+ccmp'
set wireless.wifinet{0}{1}.disassoc_low_ack='0'
set wireless.wifinet{0}{1}.wps_pushbutton='0'
set wireless.wifinet{0}{1}.network='{1}'
set wireless.wifinet{0}{1}.ssid='{2}'
set wireless.wifinet{0}{1}.key='{3}'
set wireless.wifinet{0}{1}.ieee80211r='1'
set wireless.wifinet{0}{1}.ft_over_ds='0'
set wireless.wifinet{0}{1}.ft_psk_generate_local='1'
set wireless.wifinet{0}{1}.disabled='0'
""".format(w, i, interface_config[i][2], interface_config[i][3])
                ret_conf_list.append(cmd_intf); cmd_intf = ""

        # TODO: isolate each device in the guest/iot network
        # Client Isolation is a security feature that prevents wireless clients on that network from interacting with each other, which can be enabled on networks in AP mode.
        # config 'wifi-iface'
        #   option 'mode'       'ap'
        #   option 'isolate'    '1'

    if create_wan:
        cmd_intf += """
set network.wan='interface'
set network.wan.proto='dhcp'
set network.wan6='interface'
set network.wan6.proto='dhcpv6'
"""

    # set lan IP
    ipnet = get_network_addr(ipaddr_lan)
    if ipnet == None:
        L.warning("1 unable to get network address for '{0}'".format(ipaddr_lan))
    else:
        cmd_intf += "\n"
        cmd_intf += getconf_set_network(ipnet, 'lan')
        #cmd_intf += "set network.lan.ip6assign='{0}'\n".format('')
        cmd_intf += "del network.lan.ip6assign\n"

    cmd_intf += """
delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname
"""
    ret_conf_list.append(cmd_intf); cmd_intf = ""

    # set WAN6 IPv6 prefix length
    # config interface 'wan6'
	#    option ifname 'eth0.2'
	#    option proto 'dhcpv6'
	#    option reqaddress 'try'
	#    option reqprefix '48'
    cmd_intf += "\n"
    cmd_intf += "set network.wan6.reqprefix='48'\n"

    if is_dsa:
        if trunk_bridge_device_name == 'br-lan':
            # the LAN is in the same bridge as other VLANs
            cmd_intf += """
set network.lan.device='br-lan.1'
"""
        else:
            cmd_intf += """
set network.lan.device='br-lan'
"""
        if not has_subnet_ips:
            # L.debug(f"caller set has_subnet_ips={has_subnet_ips}; so delete wan/wan6")
            # edge router
            # remove wan interfaces
            cmd_intf += """
delete network.wan
delete network.wan6
"""
        else:
            # main router
            # set separated wan/lan
            ifname ='br-lan.2'
            ifname = port_map["WAN"][0]
            cmd_intf += """
set network.wan.device='{0}'
set network.wan6.device='{0}'
""".format(ifname)

    else:
        # swconfig, openwrt 19 and lower
        cmd_intf += """
set network.lan.type='bridge'
"""
        if cb_vlan_ifname:
            if "1" in port_map:
                cmd_intf += "set network.lan.ifname='{0}'\n".format(cb_vlan_ifname(1))
            L.debug(f"check cb_vlan_ifname(2)={cb_vlan_ifname(2)}")
            if cb_vlan_ifname(2):
                cmd_intf += """
set network.wan.type='bridge'
set network.wan6.type='bridge'
"""
                cmd_intf += "set network.wan.ifname='{0}'\n".format(cb_vlan_ifname(2))
                cmd_intf += "set network.wan6.ifname='{0}'\n".format(cb_vlan_ifname(2))
        else:
            if "1" in port_map:
                cmd_intf += "set network.lan.ifname='{0}.{1}'\n".format(port_map["1"][1], 1) # the "1" is LAN
            cmd_intf += """
set network.wan.type='bridge'
set network.wan6.type='bridge'
"""
            cmd_intf += "set network.wan.ifname='{0}.{1}'\n".format(port_map["WAN"][1], 2)
            cmd_intf += "set network.wan6.ifname='{0}.{1}'\n".format(port_map["WAN"][1], 2)

    ret_conf_list.append(cmd_intf); cmd_intf = ""

    return ret_conf_list


## generate command line for a list of port and vlans pairs (port_list -- vlan_list)
#  @param port_map The port map from external name to internal id/name, such as port_map = {'CPU': [0, None], 'WAN': [1, 'eth0'], 'LAN1': [2, 'eth1']}; port_map = {'g1': 'g1', 'WAN': 'Gi0/1'}
#  @param vlan_set A full vlan set, example {5,6,10,20,...,120}
#  @param vlan_list The vlan id list for each port in ports_list; the values: -1 -- ignore, 0 -- trunk, 1-1024 -- vlan id
#  @param port_list A list of port, which names are the keys of port_map
#  @param special_vlan_set A list of vlan that are local only(not to be part of a trunk port)
#  @param support_vid If the HW support vid
# The port_map should include all of port information, such as 'CPU', 'WAN', 'LAN1', etc.
def getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set0, switch_name="switch0", special_vlan_set={1,2}, support_vid=True, support_vlan4k=False):

    cmd_switch="uci batch << EOF"

    vlan_set = {1,2}.union(vlan_set0)
    #vlan_set = vlan_set.union({ vlan_list[i] for i in range(0,len(vlan_list)) })
    for i in vlan_list:
        if isinstance(i, list):
            vlan_set = vlan_set.union(set(i))
        else:
            vlan_set = vlan_set.union({i})
    vlan_set.remove(0)

    vlan_num = 1
    for vlanid in sorted(vlan_set):
        str_ports = ""
        # assert(len(vlan_list) == len(port_list), f"the length of the vlan_list and port_list shoudl equal")
        for i in range(0,len(vlan_list)):

            vlan1 = vlan_list[i]
            if not isinstance(vlan1, list):
                vlan1 = [ vlan_list[i] ]
            for v in vlan1:
                if v == 0:

                    if (vlanid in special_vlan_set) and (not port_list[i] == 'CPU') and (not port_list[i] == 'CPU2'):
                        continue
                    if vlanid == 2:
                        if 'CPU2' in port_map:
                            if "CPU2".__eq__(port_list[i]):
                                str_ports += " {0}t".format(port_map[port_list[i]][0])
                            continue
                    if "CPU2".__eq__(port_list[i]):
                        continue
                    str_ports += " {0}t".format(port_map[port_list[i]][0])

                elif v == vlanid:
                    str_ports += " {0}".format(port_map[port_list[i]][0])
        if support_vid:
            cmd_switch += """
# VLAN{0}={1} at HW port {2}
add network switch_vlan
set network.@switch_vlan[-1].device='{3}'
set network.@switch_vlan[-1].vlan='{0}'
set network.@switch_vlan[-1].vid='{1}'
set network.@switch_vlan[-1].ports='{2}'
""".format(vlan_num, vlanid, str_ports.strip(), switch_name)
        else:
            cmd_switch += """
# VLAN{0}={1} at HW port {2}
add network switch_vlan
set network.@switch_vlan[-1].device='{3}'
set network.@switch_vlan[-1].vlan='{1}'
set network.@switch_vlan[-1].ports='{2}'
""".format(vlan_num, vlanid, str_ports.strip(), switch_name)
        #set network.@switch_vlan[-1].description='vlan-xxxx'

        vlan_num += 1

    # check switch section
    if support_vlan4k:
        cmd_switch += "set network.@switch[-1].enable_vlan4k=1\n"

    cmd_switch += """commit
EOF
"""
    #L.info("getconf_vlan cmd=" + cmd_switch)
    return cmd_switch


def getconf_access_server(param = {}):
    # todo: check param
    cmd_intf="uci batch << EOF\n"
    for i in param["zones_from"]:
        #print(f"process zone: {i}")
        if i == param["zone_server"]: continue

        cmd_intf += """
add firewall rule
set firewall.@rule[-1].name='{3}{0}'
set firewall.@rule[-1].src='fw_{0}'
set firewall.@rule[-1].dest='fw_{1}'
set firewall.@rule[-1].dest_ip='{2}'
set firewall.@rule[-1].dest_port='{4}'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'
""".format(i, param["zone_server"], param["ip"], param["prefix"], param["dest_port"])

    cmd_intf += """commit
EOF
"""
    return cmd_intf

def getconf_dns_server(param = {}):
    # todo: check param
    cmd_intf="uci batch << EOF\n"
    for i in param["zones_from"]:
        cmd_intf += """add_list dhcp.{0}.dhcp_option='6,{1}'
""".format(i, param["ip"])
    cmd_intf += """commit
EOF
"""
    return cmd_intf


def getconf_wan_port(param = {}):
    # todo: check param
    # set firewall reflection to '1' to access the host from local, NOT WORK?
    cmd_intf="""uci batch << EOF
add firewall redirect
set firewall.@redirect[-1].target='DNAT'
set firewall.@redirect[-1].name='{0}'
set firewall.@redirect[-1].src='wan'
set firewall.@redirect[-1].src_dport='{1}'
set firewall.@redirect[-1].dest_ip='{3}'
set firewall.@redirect[-1].dest_port='{4}'
set firewall.@redirect[-1].reflection='1'
""".format(param["name"], param["port"], param["zone_server"], param["ip"], param["dest_port"])
    for i in param["protocol"]:
        cmd_intf += """add_list firewall.@redirect[-1].proto='{0}'
""".format(i)

    cmd_intf += """commit
EOF
"""
    return cmd_intf

#execute_uci_command_list(pexp, [], cmd_list)
def execute_uci_command_list(pexp, prompt, cmd_list):
    #L.debug(f"try to setup cmd_list={cmd_list}")
    for i in cmd_list:
        L.debug("interface cmd=" + i)
        pexp.sendline("uci batch << EOF\n" + i + "\nEOF\n\n")
        L.debug("expect: " + str(prompt))
        ret = pexp.expect(["Entry not found"] + prompt)
        if (ret == 0):
            L.error("execute_uci_command_list() command not execed successfully")
            return False

    L.debug("uci commit ...")
    pexp.sendline("uci commit")
    return True

################################################################################
## generate the port list for vlan
class VlanPortGenerator():
    def __init__(self, port_map, port_list, vlan_list):
        self.port_map = port_map
        self.port_list = port_list
        self.vlan_list = vlan_list
        self.special_vlan_set = {1,2} # the vlan list to avoid using out of device

    # get ifname port list for openwrt SW vlan
    #port_map = {
    #    'CPU': [ None, None ],
    #    'WAN': [ 'eth0', 'eth0' ],
    #    '1': [ 'eth1', 'eth1' ],
    #    '2': [ 'eth2', 'eth2' ],
    #    '3': [ 'eth3', 'eth3' ],
    #    '4': [ 'eth4', 'eth4' ],
    #}
    #port_list = [ 'CPU', 'WAN', '1', '2', '3', '4', ]
    #vlan_list = [     0,     2,   1,  10,  10,  10, ]
    # get the port list for a vlan
    # return a string contains the config for a ifname or vlan port
    def get_port_list_ifname(self, vlanid):
        str_ports = ""
        for i in range(0,len(self.vlan_list)):
            if not (self.port_list[i] in self.port_map):
                continue
            if not self.port_map[self.port_list[i]][0]:
                continue
            vlan1 = self.vlan_list[i]
            if not isinstance(vlan1, list):
                vlan1 = [ self.vlan_list[i] ]
            for v in vlan1:
                if v == 0:
                    if (vlanid in self.special_vlan_set) and (not self.port_list[i] == 'CPU'):
                        pass
                    else:
                        str_ports += " {0}.{1}".format(self.port_map[self.port_list[i]][0], vlanid)
                if v == vlanid:
                    str_ports += " {0}".format(self.port_map[self.port_list[i]][0])
        return str_ports.strip()

    # get the vlan port list for openwrt HW switch
    #port_map = { 'CPU': [0, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
    #port_list = ['CPU', 'WAN', '1','2','3','4', ]
    #vlan_list = [    0,     2,   1, 30, 20, 50, ]
    def get_port_list_vlan(self, vlanid):
        str_ports = ""
        for i in range(0,len(self.vlan_list)):
            vlan1 = self.vlan_list[i]
            if not isinstance(vlan1, list):
                vlan1 = [ self.vlan_list[i] ]
            for v in vlan1:
                if v == 0:
                    if (vlanid in self.special_vlan_set) and (not self.port_list[i] == 'CPU') and (not self.port_list[i] == 'CPU2'):
                        continue
                    if vlanid == 2:
                        if 'CPU2' in self.port_map:
                            if "CPU2".__eq__(self.port_list[i]):
                                str_ports += " {0}t".format(self.port_map[self.port_list[i]][0])
                            continue
                    if "CPU2".__eq__(self.port_list[i]):
                        continue
                    str_ports += " {0}t".format(self.port_map[self.port_list[i]][0])

                elif v == vlanid:
                    str_ports += " {0}".format(self.port_map[self.port_list[i]][0])
        return str_ports.strip()

################################################################################
class OpenwrtSwitch(Switch):
    def __init__(self):
        super().__init__()

    # save the current config to disk
    def save_config(self):
        self.pexp.sendline("uci commit\r\n")
        self.pexp.sendline('/etc/init.d/network restart')
        time.sleep(2)
        prompt = [ "root@.*:/#" ]
        ret = self.pexp.expect(["Entry not found"] + prompt)
        #self.pexp.expect('br-lan: link becomes ready')
        self.pexp.sendline('/etc/init.d/firewall restart')
        time.sleep(2)
        prompt = [ "root@.*:/#" ]
        ret = self.pexp.expect(["Entry not found"] + prompt)
        #self.pexp.expect("* Running script '/etc/firewall.user'")
        self.pexp.sendline('/etc/init.d/dnsmasq restart')
        time.sleep(2)
        prompt = [ "root@.*:/#" ]
        ret = self.pexp.expect(["Entry not found"] + prompt)
        #self.pexp.expect("udhcpc: lease of")
        self.pexp.sendline("/etc/init.d/system reload\n")
        time.sleep(2)
        prompt = [ "root@.*:/#" ]
        ret = self.pexp.expect(["Entry not found"] + prompt)
        if (ret == 0):
            L.error("save_config() command not execed successfully")
            return False
        return True

    # reboot system
    def reboot(self, wait_network=True):
        L.info("reboot -f ...")
        self.pexp.sendline('sync')
        self.pexp.sendline('reboot -f')
        self.pexp.expect([ 'reboot: Restarting system', 'U-Boot' ])
        L.info("reboot starting ...")
        self.pexp.expect('Please press Enter to activate this console.')
        L.info("enter to console ...")
        self.pexp.sendline('\r\n\r\n')
        self.pexp.expect('built-in shell')
        L.info("got a shell")
        if wait_network:
            L.info("waiting for network link ready ...")
            self.pexp.expect(['\) entered forwarding state', 'br-lan: link becomes ready', 'internet: link becomes ready', 'wan: link becomes ready'])
            L.info("brought the network interfaces up.")
        time.sleep(5)

    def _is_dsa(self):
        # if grep -sq DEVTYPE=dsa /sys/class/net/*/uevent; then echo "IsDSA"; else echo "NotDSA"; fi
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\r\n")
        self.pexp.sendline('\nif grep -sq DEVTYPE=dsa /sys/class/net/*/uevent; then echo "Is""DSA"; else echo "Not""DSA"; fi\r\n')
        ret = self.pexp.expect(['IsDSA', 'NotDSA'])
        #L.debug(f"is_dsa?ret={ret}")
        return (ret == 0)

    # get swconfig config
    def get_swconfig(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\r\n")
        self.pexp.sendline('\necho -n -e "get_swconfig_""begin\\n" ; swconfig list ; echo "get_swconfig_""end"\r\n')
        # sample output:

        # Asus RT-N56U
        # Found: switch0 - rtl8367

        # TP-Link Archer C6 v2 (US) / A6 v2 (US/TW)
        # Found: switch0 - mdio.0

        # TP-Link Archer C7 v2
        # Found: switch0 - mdio-bus.0

        # Found: switch0 - MT7530
        # Found: switch0 - mt7530

        # Ubiquiti UniFi6 Lite
        # /bin/ash: swconfig: not found

        self.pexp.expect('get_swconfig_begin')
        self.pexp.expect('get_swconfig_end')
        ln_before = self.pexp.before.decode('UTF-8')
        #ln_after = self.pexp.after.decode('UTF-8')
        L.debug("get_swconfig ln_before=" + str(ln_before))
        #L.debug("get_swconfig ln_after=" + str(ln_after))
        return parse_swconfig_line(ln_before)

    ## detect if HW support vid
    def swconfig_support_vid(self):
        # swconfig dev switch0 help | grep -A 3 -- '--vlan'
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\r\n")
        self.pexp.sendline("swconfig dev switch0 help\n")
        self.pexp.sendline('\necho -n -e "swconfig_support_vid_""begin\\n" ; swconfig dev switch0 help ; echo "swconfig_support_vid_""end"\r\n')

        self.pexp.expect('swconfig_support_vid_begin')
        self.pexp.expect('swconfig_support_vid_end')
        ln_before = self.pexp.before.decode('UTF-8')
        L.debug("swconfig_support_vid ln_before=" + str(ln_before))
        return parse_swconfig_support_vid_line(ln_before)

    ## detect if HW support vlan4k
    def swconfig_support_vlan4k(self):
        # swconfig dev switch0 help | grep -A 3 -- '--vlan'
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\r\n")
        self.pexp.sendline("swconfig dev switch0 help\n")
        self.pexp.sendline('\necho -n -e "swconfig_support_vlan4k_""begin\\n" ; swconfig dev switch0 help ; echo "swconfig_support_vlan4k_""end"\r\n')

        self.pexp.expect('swconfig_support_vlan4k_begin')
        self.pexp.expect('swconfig_support_vlan4k_end')
        ln_before = self.pexp.before.decode('UTF-8')
        L.debug("swconfig_support_vlan4k ln_before=" + str(ln_before))
        return parse_swconfig_support_vlan4k_line(ln_before)

    def reset_config(self, port_map):
        ret_val = True
        #self.pexp.sendcontrol('c')
        L.debug("cd /")
        self.pexp.sendline("\ncd /\n")

        ret = 1
        if not self.is_gns3:
            L.debug("set default time zone")
            self.set_timezone()
            L.debug("set default hostname")
            self.set_hostname('OpenWrt')
            L.debug("set default LAN")
            self.pexp.sendline('uci set network.lan.netmask=255.255.255.0')
            self.pexp.sendline('uci set network.lan.ipaddr=192.168.2.1')
            self.pexp.sendline('uci commit')

            L.info("mount_root ...")
            self.pexp.sendline('mount_root')

            L.info("firstboot -y ...")
            self.pexp.sendline('firstboot -y')
            #self.pexp.expect('This will erase all settings and remove any installed packages. Are you sure? [N/y]')
            self.pexp.expect(['only erasing files', 'will be erased on next mount'])

            self.reboot()

            self.pexp.sendline('ip a s dev br-lan | grep "inet "')
            ret = self.pexp.expect(['    inet 192.168.1.1/24 brd 192.168.1.255 scope global br-lan', 'scope global br-lan', "ip: can't find device"])
            L.debug(f"ip a return {ret}")

        if ret > 0:
            hostname = self.get_hostname()
            L.warning('unable to FW reset the OpenWrt router.')
            # try to simulate reset
            prompt = [ "root@{0}:/#".format(hostname), "root@.*:/#" ]

            port_list = sorted(port_map)
            vlan_list = [1 for i in range(0,len(port_list))]
            for i in range(0,len(vlan_list)):
                if port_list[i] == 'CPU':
                    vlan_list[i] = 0
                elif port_list[i] == 'CPU2':
                    vlan_list[i] = 0
                elif port_list[i] == 'WAN':
                    vlan_list[i] = 2
            ifname_gen = VlanPortGenerator(port_map, port_list, vlan_list)

            L.info("try to reset device by reconfig to default with command line ...")
            ret_val = self.reset_config_sim(prompt, port_map, ifname_gen=ifname_gen)

        L.info("reset_config DONE, ret={0}".format(ret_val))
        return ret_val

    def get_version(self):
        self.pexp.sendline('\necho "get_version_""begin" ; cat /etc/openwrt_release | grep DISTRIB_RE ; echo "get_version_""end"\n')
        #self.pexp.expect('get_version_begin')
        self.pexp.expect('get_version_end')
        ln_before = self.pexp.before.decode('UTF-8')
        #ln_after = self.pexp.after.decode('UTF-8')
        #L.debug("get_version ln_before=" + str(ln_before))
        #L.debug("get_version ln_after=" + str(ln_after))
        return parse_version(ln_before)

    def _get_target(self):
        self.pexp.sendline('\necho "get_target_""begin" ; cat /etc/openwrt_release | grep DISTRIB_TARGET ; echo "get_target_""end"\n')
        #self.pexp.expect('get_target_begin')
        self.pexp.expect('get_target_end')
        ln_before = self.pexp.before.decode('UTF-8')
        #ln_after = self.pexp.after.decode('UTF-8')
        #L.debug("get_target ln_before=" + str(ln_before))
        #L.debug("get_target ln_after=" + str(ln_after))
        return parse_target(ln_before) # ath79/generic

    def _get_board(self):
        self.pexp.sendline("\r\n")
        # cat /tmp/sysinfo/board_name
        #tplink,archer-c7-v2
        # cat /tmp/sysinfo/model
        #TP-Link Archer C7 v2
        self.pexp.sendline('\necho -n -e "get_board_""begin" ; cat /tmp/sysinfo/board_name ; echo "get_board_""end"\r\n')
        self.pexp.expect('get_board_begin')
        self.pexp.expect('get_board_end')
        ln_before = self.pexp.before.decode('UTF-8')
        #ln_after = self.pexp.after.decode('UTF-8')
        #L.debug("get_board_name ln_before=" + str(ln_before))
        #L.debug("get_board_name ln_after=" + str(ln_after))
        return parse_board_line(ln_before) #tplink,archer-c7-v2

    def get_board(self):
        target = self._get_target()
        board = self._get_board()
        return target + "/" + board.replace(",", "_")

    def get_model_name(self):
        #L.debug("serial isalive? {0}".format(self.pexp.isalive()))
        assert(self.pexp.isalive())
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\r\n")
        # cat /tmp/sysinfo/model
        #TP-Link Archer C7 v2
        self.pexp.sendline('\necho -n -e "get_model_""begin" ; cat /tmp/sysinfo/model ; echo "get_model_""end"\r\n')
        self.pexp.expect('get_model_begin')
        self.pexp.expect('get_model_end')
        ln_before = self.pexp.before.decode('UTF-8')
        #ln_after = self.pexp.after.decode('UTF-8')
        #L.debug("get_model_name ln_before=" + str(ln_before))
        #L.debug("get_model_name ln_after=" + str(ln_after))
        return parse_model_line(ln_before)

    def get_hostname(self):
        # uci -p get system.@system[0].hostname
        self.pexp.sendline('\necho "get_hostname_""begin" ; uci show system | grep "hostname=" ; echo "get_hostname_""end"\n')
        #self.pexp.expect('get_hostname_begin')
        if 0 == self.pexp.expect(['get_hostname_end']):
            ln_before = self.pexp.before.decode('UTF-8')
            return parse_hostname(ln_before)
        return None

    def set_hostname(self, hostname):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        L.info("set_hostname({0}) ...".format(hostname))
        self.pexp.sendline("uci set system.@system[0].hostname='{0}'".format(hostname))
        self.pexp.sendline("hostname '{0}'".format(hostname))
        self.pexp.sendline("uci get system.@system[0].hostname")
        self.pexp.expect(hostname)

        self.pexp.sendline("uci commit system")
        self.pexp.sendline("/etc/init.d/system reload")
        time.sleep(1)

        return True

    # get a list of VLAN id
    def get_vlans(self):
        if self.has_hw_switch:
            "uci show network | grep vlan= | awk -F= '{print $2}'"
            # network.@switch_vlan[0].vlan='1'
        else:
            "uci show network | grep ifname"
            # network.coredata.ifname='eth4.10'
            # network.office.ifname='eth3 eth4.20'
        return None

    # the bridge for DSA interfaces
    br_trunk = None
    # setup the br_trunk, if we need to use a different name other than 'br-lan'
    def setup_br_trunk(self, port_list = [], vlan_list = []):
        if len(port_list) != len(vlan_list):
            L.error("parameter list not equal!")
            L.error(f"port_list len={len(port_list)}, {port_list}")
            L.error(f"vlan_list len={len(vlan_list)}, {vlan_list}")
            return False
        # if set, ignore
        if self.br_trunk: return True

        self.br_trunk = 'br_trunk'
        # if the LAN (VLAN 1) need to be accessed in one of ethernet ports,
        # we'll use 'br-lan' for both the LAN and other VLANs
        for idx, x in enumerate(port_list):
            if x == "CPU": continue
            if x == "CPU2": continue
            if vlan_list[idx] == 1:
                # the VLAN 1 is for LAN
                self.br_trunk = 'br-lan'

        return True

    # for DSA
    def _setup_lan_trunk_bridge(self, port_map, port_list, has_subnet_ips):

        # TODO:
        # uci show network | grep ".device\[.*\]=" | sort | uniq | wc -l
        # uci show network.@device[0]
        # uci show network.@device[0].name | grep br-lan
        # echo "network.cfg040f15.name='br-lan'" | awk -F= '{print $1}' | awk -F. '{print $2}'
        # uci get network.cfg040f15.ports
        # uci delete network.cfg040f15.ports

        # remove old br-lan
        # if self.br_trunk == 'br-lan':
        #     self.pexp.sendline("""uci show network | grep -e "network.@device.*.name='br-lan'" | awk -F\] '{print $1 "]" }' | xargs -n 1 uci delete;""")
        # else:
        #     self.pexp.sendline("""N=$(uci show network.@device[0].name | grep br-lan | awk -F= '{print $1}' | awk -F. '{print $2}'); uci delete network.$N.ports; uci add_list network.$N.ports='br-lan';""")
        # delete the old 'br-lan':
        self.pexp.sendline("""uci show network | grep -e "network.@device.*.name='br-lan'" | awk -F\] '{print $1 "]" }' | xargs -n 1 uci delete;""")
        self.pexp.sendline("""uci show network | grep -e "network.@device.*.name='br_trunk'" | awk -F\] '{print $1 "]" }' | xargs -n 1 uci delete;""")
        if self.br_trunk != 'br-lan':
            # restore a new 'br-lan'
            str_conf = """add network device
set network.@device[-1].name='{0}'
set network.@device[-1].type='bridge'
""".format('br-lan')
            prompt = [ "root@OpenWrt:/#", "root@.*:/#" ]
            execute_uci_command_list(self.pexp, prompt, [ str_conf ])

        # restore the 'br_trunk': (or 'br-lan' if the two are equal)
        str_conf = _getconf_trunk_bridge_device(port_map, port_list, self.br_trunk, has_subnet_ips)
        L.debug("_getconf_trunk_bridge_device() return {}".format(str_conf))
        prompt = [ "root@OpenWrt:/#", "root@.*:/#" ]
        execute_uci_command_list(self.pexp, prompt, [ str_conf ])

    # vlan_set: the set of vlan id
    # vlan_list: the vlan id list for each port, -1 -- ignore, 0 -- trunk, 1-1024 -- vlan id
    # port_list: the port list
    def set_vlans(self, port_map, port_list, vlan_list, vlan_set, interface_config={}):
        self.set_clock()
        has_subnet_ips = interfaces_has_subnet_ips(interface_config)
        L.debug("set_vlans() arg has_subnet_ips={}".format(has_subnet_ips))

        #if not self.has_hw_switch:
        #    L.warning("no switch HW, skip set vlans")
        #    return True

        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        swconf = self.get_swconfig()
        if swconf:
            if self.has_hw_switch:
                # delete old vlan settings
                L.info("reset 'network.@switch_vlan' ...")
                self._remove_section_filter("network", "switch_vlan")
                support_vid = self.swconfig_support_vid()
                support_vlan4k = self.swconfig_support_vlan4k()

                switch_name = swconf[0]
                str_conf = getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set, swconf[0], support_vid=support_vid, support_vlan4k=support_vlan4k)
                self.pexp.sendline(str_conf)

        elif self._is_dsa():
            # TODO: get the device name 'br-lan'
            #self._remove_section_filter("network", "bridge-vlan")
            L.info("set with bridge-vlan")
            self.setup_br_trunk(port_list, vlan_list)
            self._setup_lan_trunk_bridge(port_map, port_list, has_subnet_ips)

            # setup a new br-lan to bridge all of network interfaces
            str_conf = getconf_vlan_dsa(port_map, port_list, vlan_list, vlan_set, self.br_trunk, has_subnet_ips=has_subnet_ips)
            #hostname = self.get_hostname(); prompt = [ "root@{0}:/#".format(hostname) ]
            prompt = [ "root@OpenWrt:/#", "root@.*:/#" ]
            execute_uci_command_list(self.pexp, prompt, [ str_conf ])
        else:
            L.info("system won't support either swconfig or DSA")

        L.info("set_vlans done")
        return True

    def set_timezone(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        #self.pexp.sendline("uci show system")
        import time
        tz = list(time.tzname)
        self.pexp.sendline("uci set system.@system[0].timezone='{0}'".format(tz[0]))
        self.pexp.sendline("uci commit system")
        time.sleep(1)
        return True

    # set current time to device
    def set_clock(self):
        self.set_timezone()
        self.pexp.sendline("\ncd /\n")
        from time import strftime, localtime
        str_time = strftime("%Y-%m-%d %H:%M:%S", localtime())
        L.info("clock set {0} ...".format(str_time))
        self.pexp.sendline("date -s '{0}'".format(str_time))
        L.info("clock set DONE")
        return True

    def get_clock(self):
        #L.debug("get_clock() ...")
        #self.pexp.sendline('\necho "get_clock_""begin" ; date -Isecond ; echo "get_clock_""end"\n')
        self.pexp.sendline('\necho "get_clock_""begin" ; date -R ; echo "get_clock_""end"\n')
        #self.pexp.expect('get_clock_begin')
        ret = self.pexp.expect(['get_clock_end'])
        #L.debug("clock exp ret={0}".format(ret))
        ln_before = self.pexp.before.decode('UTF-8')
        #ln_after = self.pexp.after.decode('UTF-8')
        #L.debug("get_clock ln_before=" + str(ln_before))
        #L.debug("get_clock ln_after=" + str(ln_after))
        if 0 == ret:
            return parse_clock_openwrt(ln_before)
        return None
    root_passwd = None
    def set_root_passwd(self, new_passwd):
        self.root_passwd = new_passwd

        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        self.pexp.sendline('passwd')
        self.pexp.expect('New password:')
        self.pexp.sendline(new_passwd)
        self.pexp.expect('Retype password:')
        self.pexp.sendline(new_passwd)
        self.pexp.expect('password for root changed by root')
        return True

    def _check_setup_wan(self):
        # TODO:
        # check if the wan exist (Unifi 6 Lite has no wan)
        #uci get network.wan
        self.pexp.sendline('uci get network.wan')
        ret = self.pexp.expect(['interface', 'uci: Entry not found'])
        if ret == 0:
            return True
        L.info("Not found 'wan', try to setup the local proto to DHCP")
        # if no, create one on the first LAN?
        uci_conf_list = []

        cmd_intf="""
set dhcp.lan.ignore=1
commit dhcp
set network.lan.proto=dhcp
commit network
"""
        uci_conf_list.append(cmd_intf); cmd_intf = ""
        #cmd_intf += "set network.{0}='interface'".format('lan')

        hostname = self.get_hostname()
        prompt = [ "root@{0}:/#".format(hostname) ]
        execute_uci_command_list(self.pexp, prompt, uci_conf_list)
        # self.save_config()
        self.pexp.sendline('/etc/init.d/network restart')

    def _wait_connected(self, timeout = 10):
        from datetime import datetime, timedelta

        self._check_setup_wan()
        delta = timedelta(seconds=timeout)
        tm_start = datetime.now()
        while True:
            L.info("_wait_connected() ping ...")
            url_test = "openwrt.org"
            self.pexp.sendline('ping -c 2 {0}'.format(url_test))
            expect_list = ['2 packets transmitted, 2 packets received,', '2 packets transmitted, 1 packets received', 'ping: sendto: Permission denied', "ping: bad address '{0}'".format(url_test), 'ping: sendto: Network unreachable']
            ret = self.pexp.expect(expect_list)
            L.debug(f"ping return [{ret}]={expect_list[ret]}")
            if ret < 2:
                return True
            if tm_start + delta <= datetime.now():
                L.error("can not access Internet")
                break
            time.sleep(1)

        return False

    def change_to_https(self):
        # redirect to SSL port
        ##uci set uhttpd.main.listen_http="0.0.0.0:80 [::]:80"
        ##uci set uhttpd.main.listen_https="0.0.0.0:443 [::]:443"
        #uci set uhttpd.main.redirect_https='1'
        #uci commit
        # self.pexp.sendline('uci delete uhttpd.main.listen_http && uci commit') # diable plain HTTP port
        self.pexp.sendline('uci set uhttpd.main.redirect_https=1 && uci commit')

        L.info("restart services")
        self.pexp.sendline('/etc/init.d/uhttpd restart && sleep 3 && ps | grep uhttpd')
        time.sleep(5)
        self.pexp.expect("/usr/sbin/uhttpd")
        L.info("done upgrade softwares.")
        return True

    def update_softwares(self, packages=[]):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        L.info("check connection")
        if not self._wait_connected(25):
            L.error("can not access Internet")
            return False

        L.info("opkg update")
        count = 60
        while count > 0:
            self.pexp.sendline('opkg update')
            expect_list = ['Updated list of available packages in /var/opkg-lists/openwrt_telephony', 'Failed to download the package list from', 'available on filesystem /overlay,', 'Cannot install package']
            ret = self.pexp.expect(expect_list)
            if ret > 0:
                L.error("unable to update, no connection? ret={}, msg={}".format(ret, expect_list[ret]))
                L.debug("read before=" + str(self.pexp.before))
                L.debug("read after=" + str(self.pexp.after))
                pexpect_clean_buffer(self.pexp)
            else:
                break
            count -= 1
            L.debug("count={}".format(count))
            time.sleep(5)
        if count < 1:
            L.error("Error in update")
            return False
        self.pexp.expect('Signature check passed.')

        #self.pexp.sendline('opkg list_installed > /tmp/opkg-installed.txt')
        #self.pexp.sendline('cat /tmp/opkg-installed.txt | gawk '{print $1}' | xargs -n 1 opkg upgrade')
        for i in packages:
            pkg = i.strip()
            L.info("opkg install {0} ...".format(pkg))

            count = 60
            while count > 0:
                pexpect_clean_buffer(self.pexp)
                self.pexp.sendline('opkg install {0}'.format(pkg))
                expect_list = ['Configuring {0}.'.format(pkg), 'installed in root is up to date.', 'Cannot install package', 'Unknown package', 'Failed to download']
                ret = self.pexp.expect(expect_list)
                if ret < 1:
                    break
                elif ret < 4:
                    L.warning(f"Warning: pkg={pkg}: {expect_list[ret]}")
                    break
                else:
                    L.error("unable to install '{}', no connection? ret={}, msg={}".format(pkg, ret, expect_list[ret]))
                    L.debug("read before=" + str(self.pexp.before))
                    L.debug("read after=" + str(self.pexp.after))
                count -= 1
                L.debug("count={}".format(count))
                time.sleep(5)
            if count < 1:
                L.error("Error in install package {}".format(pkg))
                return False
        return self.change_to_https()

    # fix mesh driver problem
    # ref: https://cgomesu.com/blog/Mesh-networking-openwrt-batman/#hardware
    def fix_kmod_mesh(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        self.pexp.sendline("opkg remove ath10k-firmware-qca9888-ct kmod-ath10k-ct")

        self.pexp.sendline("opkg update && opkg install ath10k-firmware-qca9888 kmod-ath10k")
        return True

    # install wake on lan when detecting a connection to the speific hosts
    # ref: http://jazz.tvtom.pl/waking-server-incoming-connection/
    # opkg update
    # opkg install bash curl conntrack owipcalc etherwake uuidgen
    #def install_wol(self):
    #    self.update_softwares(['bash', 'curl', 'conntrack', 'owipcalc', 'etherwake', 'uuidgen'])

    def install_hnet(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        # TODO: the dhcp need to be adjusted before replacing the odhcpd-ipv6only!!
        self.pexp.sendline('mount -o remount,rw /')
        self.pexp.sendline('opkg remove odhcpd-ipv6only && opkg install hnet-full luci-compat')
        self.pexp.expect(['Configuring hnet-full.', 'Package luci-compat .* installed in root is up to date.'])
        self.pexp.sendline('opkg install ipset ip tcpdump strace')
        self.pexp.expect(['Configuring ipset.', 'Package strace .* installed in root is up to date.'])


    def show_network(self):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        L.info("get HW switch info")
        swconf = self.get_swconfig()
        if swconf:
            self.pexp.sendline(f"swconfig dev {swconf[0]} show | grep 'ports:'")

        self.pexp.sendline("uci show network")
        self.pexp.sendline("uci get network.@switch[0]")
        self.pexp.sendline("uci get network.@switch[0].name")
        # Show info:
        '''uci show network; uci show dhcp
ip a; ip -4 r; ip -4 ru; ip -6 r; ip -6 ru
ls -l /etc/resolv.* /tmp/resolv.*
head -n -0 /etc/resolv.* /tmp/resolv.*
'''

    # uci remove items filtered by filter in section
    def _remove_section_filter(self, section, filter):
        cmd = "echo 'remove_config_''begin' && uci show " + \
            str(section) + " |  awk -F. '{print $2}' | grep = | awk -F= '{print $1}' | grep '" + \
            str(filter) + "' | sort -r | uniq | while read a; do uci delete " + \
            str(section) + ".$a; done"

        #L.info("cmd=" + cmd)
        prompt = [ "root@OpenWrt:/#", "root@.*:/#" ]

        while True:
            self.pexp.sendline('\n' + cmd + "\n")
            time.sleep(1)
            ret = self.pexp.expect('remove_config_begin')
            #ln_before = self.pexp.before.decode('UTF-8')
            #ln_after = self.pexp.after.decode('UTF-8')
            #L.debug("rm sec ln_before=" + str(ln_before))
            #L.debug("rm sec ln_after=" + str(ln_after))
            ret = self.pexp.expect(['Entry not found'] + prompt)
            #ln_before = self.pexp.before.decode('UTF-8')
            ln_after = self.pexp.after.decode('UTF-8')
            #L.debug("rm sec 2 ln_before=" + str(ln_before))
            #L.debug("rm sec 2 ln_after=" + str(ln_after))
            if not re.search('Entry not found', ln_after):
                break
            time.sleep(1)

    def check_file_exist(self, file_name):
        #L.debug(f"check_file_exist({file_name}) ...")
        prompt = [ "root@OpenWrt:/#", "root@.*:/#" ]
        self.pexp.sendline(f'\necho "check_file_exist_""is_begin" ; if [ -f "{file_name}" ]; then echo EXIST; else echo None ; fi ; echo "check_file_exist_""end"\n')
        ret = self.pexp.expect('check_file_exist_is_')
        ret = self.pexp.expect([f'begin{file_name}', 'No such file or directory'] + prompt)
        ln_before = self.pexp.before.decode('UTF-8').strip()
        #L.debug("check_file_exist ln_before=" + str(ln_before))
        if "EXIST" in ln_before:
            #L.debug(f"file exist: {file_name}")
            return True
        #L.debug(f"file NOT exist: {file_name}")
        return False

    def get_dns_resolv_file(self):
        dns_resolv_file = "/tmp/resolv.conf.d/resolv.conf.auto"
        if not self.check_file_exist(dns_resolv_file):
            dns_resolv_file = "/tmp/resolv.conf.auto"
        return dns_resolv_file

    def reset_config_sim(self, prompt, port_map, ifname_gen=None):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        dns_resolv_file = self.get_dns_resolv_file()
        L.info(f"DNS resolv file = {dns_resolv_file}")

        #uci show firewall | awk -F. '{print $2}' | awk -F= '{print $1}' | sort -r | uniq | while read a; do echo uci delete firewall.$a; done
        for i in [ 'network', 'firewall', 'dhcp', 'system' ]:
            L.info("reset '{0}' ...".format(i))
            self._remove_section_filter(i, "")

        self.pexp.sendline('uci commit')

        def cb_vlan_ifname1(vlanid):
            return ifname_gen.get_port_list_ifname(vlanid)
        cb_vlan_ifname = None
        if not None == ifname_gen:
            cb_vlan_ifname = cb_vlan_ifname1

        if self.has_hw_switch:
            swconf = self.get_swconfig()
            if swconf:
                support_vlan4k=self.swconfig_support_vlan4k()
                cmd_intf = getconf_default_vlan_swconfig(port_map, swconf[0], support_vlan4k=support_vlan4k)
                self.pexp.sendline(cmd_intf)
            else:
                L.warning("not found swconfig! ignore default VLAN")

        L.info("setup default network ...")
        dev_lan = None
        if "1" in port_map:
            dev_lan = port_map["1"][1]
        dev_wan = port_map["WAN"][1]

        cmd_intf = getconf_default_network(cb_vlan_ifname, dev_lan=dev_lan, dev_wan=dev_wan, dns_resolv_file=dns_resolv_file)
        #L.debug("default net cmd=" + cmd_intf)
        self.pexp.sendline(cmd_intf)
        #L.debug("expect: " + str(prompt))
        ret = self.pexp.expect(["Entry not found"] + prompt)
        if (ret == 0):
            L.error("reset_config_sim() command not execed successfully")
            return False
        L.info("end of reset_config_sim")
        return True


    def set_interfaces(self, ipaddr_lan, interface_config, port_map, ifname_gen=None):
        #L.debug(f"set_interfaces(ipaddr_lan={ipaddr_lan}; interface_config={interface_config}; ifname_gen={ifname_gen})")
        if not interface_config:
            L.error("not specify the interface config")
            return False
        #self.setup_br_trunk(port_list, vlan_list)

        hostname = self.get_hostname()
        prompt = [ "root@{0}:/#".format(hostname) ]
        # prompt = [ "root@{0}:/#".format(hostname), "root@.*:/#" ]

        version = self.get_version()
        ver = int(version.split(".")[0])

        def cb_vlan_ifname1(vlanid):
            return ifname_gen.get_port_list_ifname(vlanid)
        cb_vlan_ifname = None
        if not None == ifname_gen:
            cb_vlan_ifname = cb_vlan_ifname1
        L.debug("cb_vlan_ifname=" + str(cb_vlan_ifname))

        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        # remove other interfaces
        cmd = """uci show network | awk -F= '{print $1}' | awk -F. '{print $1 "." $2}' | sort | uniq | grep -v switch | grep -v device | grep -v bridge-vlan | grep -v network.loopback | grep -v network.lan | grep -v network.wan | grep -v network.globals | while read a; do uci delete $a; done"""
        self.pexp.sendline(cmd)

        num_wifi = 0
        self.pexp.sendline('iw dev')
        iw_exp = ["Interface wlan0", "iw: not found"]
        ret = self.pexp.expect(iw_exp)
        if ret == 0:
            self.pexp.sendline('echo "get_wifi_""begin" ; iw dev ; echo "get_wifi_""end"')
            self.pexp.expect('get_wifi_end')
            ln_before = self.pexp.before.decode('UTF-8')
            #ln_after = self.pexp.after.decode('UTF-8')
            #L.debug("wifi ln_before=" + str(ln_before))
            #L.debug("wifi ln_after=" + str(ln_after))
            num_wifi = get_hw_wifi_number(ln_before)
        else:
            L.warning("cant find iw dev {0}: '{1}'".format(ret, iw_exp[ret]))

        if num_wifi > 0:
            L.info("WiFi devices detected")
        else:
            L.info("WiFi devices not found")

        # detect if the wan interface exist of a main router, if not then setup the wan
        create_wan = False
        # detect if the interface has sub-network IPs
        has_subnet_ips = interfaces_has_subnet_ips(interface_config)
        if has_subnet_ips:
            create_wan = True
            # if not exist wan:
            #     create_wan = True
        hostname = self.get_hostname()

        #L.debug(f"try to setup ipaddr_lan={ipaddr_lan}; interface_config={interface_config}; cb_vlan_ifname={cb_vlan_ifname}; num_wifi={num_wifi}")
        cmd_list = getconf_list_interfaces(hostname, ipaddr_lan, interface_config, port_map, cb_vlan_ifname, num_wifi, is_dsa=self._is_dsa(), create_wan=create_wan, has_subnet_ips=has_subnet_ips, default_passwd=self.root_passwd, trunk_bridge_device_name = self.br_trunk)
        return execute_uci_command_list(self.pexp, prompt, cmd_list)


    # add a domain name
    def add_domain(self, domain_name, ip_addr):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")

        # --address, Return ip on query domain 'domain_name' and subdomain '*.domain_name'.
        # A and AAAA RR
        self.pexp.sendline("uci add_list dhcp.@dnsmasq[0].address='/{0}/{1}'".format(domain_name, ip_addr))
        # or --host-record,
        # uci add dhcp domain
        # uci set dhcp.@domain[-1].name="mylaptop"
        # uci set dhcp.@domain[-1].ip="fdce::23"
        # uci commit dhcp

    # setup the tftp server
    # setup your tftp server to use port range 59000-59499, and then setup the firewall for 69 59000-59499 for TFTPD
    def setup_tftp_external(self, addr_tftpd = "10.1.1.23"):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")
        self.pexp.sendline("""uci set dhcp.@dnsmasq[0].enable_tftp=1
uci set dhcp.@dnsmasq[0].dhcp_boot=pxelinux.0,mytftpserver,{0}
uci commit
""".format(addr_tftpd))

    ## setup hosts that can be access by the clients from other zones
    def setup_access_server(self, param = {}):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")
        cmd_intf = getconf_access_server(param)
        #L.debug("samba cmd=" + cmd_intf)
        self.pexp.sendline(cmd_intf)

    ## setup DNS server for network
    def setup_dns_server(self, param = {}):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")
        cmd_intf = getconf_dns_server(param)
        #L.debug("samba cmd=" + cmd_intf)
        self.pexp.sendline(cmd_intf)

    ## setup exposed port for WAN
    def setup_wan_port(self, param = {}):
        #self.pexp.sendcontrol('c')
        self.pexp.sendline("\ncd /\n")
        cmd_intf = getconf_wan_port(param)
        #L.debug("samba cmd=" + cmd_intf)
        self.pexp.sendline(cmd_intf)

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

        def test_getconf_vlans_swconfig(self):
            self.maxDiff = None

            exp="""uci batch << EOF
# VLAN1=1 at HW port 0t 2
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='1'
set network.@switch_vlan[-1].vid='1'
set network.@switch_vlan[-1].ports='0t 2'

# VLAN2=2 at HW port 0t 1
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='2'
set network.@switch_vlan[-1].vid='2'
set network.@switch_vlan[-1].ports='0t 1'

# VLAN3=20 at HW port 0t 4
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='3'
set network.@switch_vlan[-1].vid='20'
set network.@switch_vlan[-1].ports='0t 4'

# VLAN4=30 at HW port 0t 3
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='4'
set network.@switch_vlan[-1].vid='30'
set network.@switch_vlan[-1].ports='0t 3'

# VLAN5=50 at HW port 0t 5
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='5'
set network.@switch_vlan[-1].vid='50'
set network.@switch_vlan[-1].ports='0t 5'
commit
EOF
"""
            port_map = { 'CPU': [0, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
            port_list = ['CPU', 'WAN', '1','2','3','4', ]
            vlan_list = [    0,     2,   1, 30, 20, 50, ]
            vlan_set = {20,30,50}
            self.assertEqual(exp, getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set, switch_name="switch0"))


            port_list = ['CPU', 'WAN', '1','2','3','4', ]
            vlan_list = [    0,     0,   1,  0, 20, 20, ]
            vlan_set = {20,30,50}
            vlan_set1 = {1,2}.union(vlan_set)
            vlan_set1 = vlan_set1.union({ vlan_list[i] for i in range(0,len(vlan_list)) })
            vlan_set1.remove(0)
            exp = """uci batch << EOF
# VLAN1=1 at HW port 0t 2
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='1'
set network.@switch_vlan[-1].vid='1'
set network.@switch_vlan[-1].ports='0t 2'

# VLAN2=2 at HW port 0t
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='2'
set network.@switch_vlan[-1].vid='2'
set network.@switch_vlan[-1].ports='0t'

# VLAN3=20 at HW port 0t 1t 3t 4 5
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='3'
set network.@switch_vlan[-1].vid='20'
set network.@switch_vlan[-1].ports='0t 1t 3t 4 5'

# VLAN4=30 at HW port 0t 1t 3t
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='4'
set network.@switch_vlan[-1].vid='30'
set network.@switch_vlan[-1].ports='0t 1t 3t'

# VLAN5=50 at HW port 0t 1t 3t
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='5'
set network.@switch_vlan[-1].vid='50'
set network.@switch_vlan[-1].ports='0t 1t 3t'
commit
EOF
"""
            self.assertEqual(exp, getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set1, switch_name="switch0"))

        def test_getconf_vlans_swconfig2(self):
            self.maxDiff = None

            exp="""uci batch << EOF
# VLAN1=1 at HW port 0t 2
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='1'
set network.@switch_vlan[-1].vid='1'
set network.@switch_vlan[-1].ports='0t 2'

# VLAN2=2 at HW port 6t 1
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='2'
set network.@switch_vlan[-1].vid='2'
set network.@switch_vlan[-1].ports='6t 1'

# VLAN3=20 at HW port 0t 4
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='3'
set network.@switch_vlan[-1].vid='20'
set network.@switch_vlan[-1].ports='0t 4'

# VLAN4=30 at HW port 0t 3
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='4'
set network.@switch_vlan[-1].vid='30'
set network.@switch_vlan[-1].ports='0t 3'

# VLAN5=50 at HW port 0t 5
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='5'
set network.@switch_vlan[-1].vid='50'
set network.@switch_vlan[-1].ports='0t 5'
commit
EOF
"""
            port_map = { 'CPU': [0, 'eth0'], 'CPU2': [6, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
            port_list = ['CPU', 'CPU2', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [    0,      0,     2,   1,  30,  20,  50, ]
            vlan_set = {20,30,50}
            #print("vlans=" + str(getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set)))
            self.assertEqual(exp, getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set, switch_name="switch0"))

        def test_getconf_vlans_swconfig3_array(self):
            self.maxDiff = None

            exp="""uci batch << EOF
# VLAN1=1 at HW port 0t 2
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='1'
set network.@switch_vlan[-1].vid='1'
set network.@switch_vlan[-1].ports='0t 2'

# VLAN2=2 at HW port 6t 1
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='2'
set network.@switch_vlan[-1].vid='2'
set network.@switch_vlan[-1].ports='6t 1'

# VLAN3=20 at HW port 0t 1t 4
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='3'
set network.@switch_vlan[-1].vid='20'
set network.@switch_vlan[-1].ports='0t 1t 4'

# VLAN4=30 at HW port 0t 1t 3
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='4'
set network.@switch_vlan[-1].vid='30'
set network.@switch_vlan[-1].ports='0t 1t 3'

# VLAN5=50 at HW port 0t 1t 5
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='5'
set network.@switch_vlan[-1].vid='50'
set network.@switch_vlan[-1].ports='0t 1t 5'
commit
EOF
"""

            port_map = { 'CPU': [0, 'eth0'], 'CPU2': [6, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
            port_list = ['CPU', 'CPU2', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [    0,      0, [0,2],   1,  30,  20,  50, ]
            vlan_set = {20,30,50}
            #print("vlans=" + str(getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set)))
            self.assertEqual(exp, getconf_vlans_swconfig(port_map, port_list, vlan_list, vlan_set, switch_name="switch0"))

        def test_getconf_interfaces_ver21(self):
            self.maxDiff = None

            expect = ["""
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1

set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1

set network.coredata='interface'

set network.coredata.type='bridge'
set network.coredata.device='br-lan.10'

set network.coredata.ip6assign='60'
set network.coredata.proto='static'
set network.coredata.ipaddr='10.1.1.1'
set network.coredata.netmask='255.255.255.248'

set dhcp.coredata='dhcp'
set dhcp.coredata.interface='coredata'
set dhcp.coredata.leasetime='4h'
set dhcp.coredata.ra_management='1'
set dhcp.coredata.dhcpv4='server'
set dhcp.coredata.dhcpv6='server'
set dhcp.coredata.ra='server'
set dhcp.coredata.start='2'
set dhcp.coredata.limit='6'
""","""
set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
del network.lan.ip6assign

delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname

set network.wan6.reqprefix='48'

set network.lan.device='br-lan.1'

set network.wan.device='wan'
set network.wan6.device='wan'
"""]
            interface_config = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "10.1.1.0/29", "", "", []],
            }
            port_map = { 'CPU': [ None, None ], 'WAN': ['wan', 'eth0'], '1': ['lan1', 'eth0'], '2': ['lan2', 'eth0'], '3': ['lan3', 'eth0'], '4': ['lan4', 'eth0'] }
            out = getconf_list_interfaces("OpenWrt", "192.168.1.0/24", interface_config, port_map, cb_vlan_ifname=None, num_wifi=2, is_dsa=True)
            #L.debug("out=" + str(out))
            self.assertEqual(expect, out)

        def test_getconf_interfaces(self):
            self.maxDiff = None

            expect = ["""
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1

set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1

set network.coredata='interface'

set network.coredata.type='bridge'
set network.coredata.ifname='eth0.10'

set network.coredata.ip6assign='60'
set network.coredata.proto='static'
set network.coredata.ipaddr='10.1.1.1'
set network.coredata.netmask='255.255.255.248'

set dhcp.coredata='dhcp'
set dhcp.coredata.interface='coredata'
set dhcp.coredata.leasetime='4h'
set dhcp.coredata.ra_management='1'
set dhcp.coredata.dhcpv4='server'
set dhcp.coredata.dhcpv6='server'
set dhcp.coredata.ra='server'
set dhcp.coredata.start='2'
set dhcp.coredata.limit='6'
""","""
set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
del network.lan.ip6assign

delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname

set network.wan6.reqprefix='48'

set network.lan.type='bridge'
set network.lan.ifname='eth0.1'

set network.wan.type='bridge'
set network.wan6.type='bridge'
set network.wan.ifname='eth0.2'
set network.wan6.ifname='eth0.2'
"""]
            interface_config = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "10.1.1.0/29", "", "", []],
            }
            port_map = { 'CPU': [0, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
            out = getconf_list_interfaces("OpenWrt", "192.168.1.0/24", interface_config, port_map, cb_vlan_ifname=None, num_wifi=2)
            #L.debug("out=" + str(out))
            self.assertEqual(expect, out)


        def test_getconf_interfaces_same_vlan(self):
            self.maxDiff = None

            # test the non-hw-switch with same VLAN
            expect = ["""
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1

set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1

set network.coredata='interface'

set network.coredata.type='bridge'
set network.coredata.ifname='eth2 eth3 eth4'

set network.coredata.ip6assign='60'
set network.coredata.proto='static'
set network.coredata.ipaddr='10.1.1.1'
set network.coredata.netmask='255.255.255.248'

set dhcp.coredata='dhcp'
set dhcp.coredata.interface='coredata'
set dhcp.coredata.leasetime='4h'
set dhcp.coredata.ra_management='1'
set dhcp.coredata.dhcpv4='server'
set dhcp.coredata.dhcpv6='server'
set dhcp.coredata.ra='server'
set dhcp.coredata.start='2'
set dhcp.coredata.limit='6'
""","""
set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
del network.lan.ip6assign

delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname

set network.wan6.reqprefix='48'

set network.lan.type='bridge'
set network.lan.ifname='eth1'

set network.wan.type='bridge'
set network.wan6.type='bridge'
set network.wan.ifname='eth0'
set network.wan6.ifname='eth0'
"""]
            interface_config = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "10.1.1.0/29", "", "", []],
            }
            port_map = {
                'CPU': [ None, None ],
                'WAN': [ 'eth0', 'eth0' ],
                '1': [ 'eth1', 'eth1' ],
                '2': [ 'eth2', 'eth2' ],
                '3': [ 'eth3', 'eth3' ],
                '4': [ 'eth4', 'eth4' ],
            }
            port_list = [ 'CPU', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [     0,     2,   1,  10,  10,  10, ]

            def cb_vlan_ifname_test1(vlanid):
                str_port = ""
                for i in range(0,len(vlan_list)):
                    if not (port_list[i] in port_map):
                        continue
                    if not port_map[port_list[i]][0]:
                        continue
                    vlan1 = vlan_list[i]
                    if not isinstance(vlan1, list):
                        vlan1 = [ vlan_list[i] ]
                    for v in vlan1:
                        if v == 0:
                            str_port += " {0}.{1}".format(port_map[port_list[i]][0], vlanid)
                        if v == vlanid:
                            str_port += " {0}".format(port_map[port_list[i]][0])
                return str_port.strip()

            out = getconf_list_interfaces("OpenWrt", "192.168.1.0/24", interface_config, port_map, cb_vlan_ifname=cb_vlan_ifname_test1, num_wifi=2)
            self.assertEqual(expect, out)


            # test the non-hw-switch with three VLANs
            expect = ["""
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1

set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1

set network.coredata='interface'

set network.coredata.type='bridge'
set network.coredata.ifname='eth2'

set network.coredata.ip6assign='60'
set network.coredata.proto='static'
set network.coredata.ipaddr='10.1.1.1'
set network.coredata.netmask='255.255.255.248'

set dhcp.coredata='dhcp'
set dhcp.coredata.interface='coredata'
set dhcp.coredata.leasetime='4h'
set dhcp.coredata.ra_management='1'
set dhcp.coredata.dhcpv4='server'
set dhcp.coredata.dhcpv6='server'
set dhcp.coredata.ra='server'
set dhcp.coredata.start='2'
set dhcp.coredata.limit='6'
""","""
set network.office='interface'

set network.office.type='bridge'
set network.office.ifname='eth3'

set network.office.ip6assign='60'
set network.office.proto='static'
set network.office.ipaddr='10.1.1.17'
set network.office.netmask='255.255.255.240'

set dhcp.office='dhcp'
set dhcp.office.interface='office'
set dhcp.office.leasetime='4h'
set dhcp.office.ra_management='1'
set dhcp.office.dhcpv4='server'
set dhcp.office.dhcpv6='server'
set dhcp.office.ra='server'
set dhcp.office.start='18'
set dhcp.office.limit='14'

add firewall zone
set firewall.@zone[-1].name='fw_office'
set firewall.@zone[-1].network='office'
set firewall.@zone[-1].input='ACCEPT'
set firewall.@zone[-1].output='ACCEPT'
set firewall.@zone[-1].forward='REJECT'
""","""
add firewall forwarding
set firewall.@forwarding[-1].dest='wan'
set firewall.@forwarding[-1].src='fw_office'
""","""
set network.game='interface'

set network.game.type='bridge'
set network.game.ifname='eth4'

set network.game.ip6assign='60'
set network.game.proto='static'
set network.game.ipaddr='10.1.1.9'
set network.game.netmask='255.255.255.248'

set dhcp.game='dhcp'
set dhcp.game.interface='game'
set dhcp.game.leasetime='4h'
set dhcp.game.ra_management='1'
set dhcp.game.dhcpv4='server'
set dhcp.game.dhcpv6='server'
set dhcp.game.ra='server'
set dhcp.game.start='10'
set dhcp.game.limit='6'

add firewall zone
set firewall.@zone[-1].name='fw_game'
set firewall.@zone[-1].network='game'
set firewall.@zone[-1].input='ACCEPT'
set firewall.@zone[-1].output='ACCEPT'
set firewall.@zone[-1].forward='REJECT'
""","""
add firewall forwarding
set firewall.@forwarding[-1].dest='wan'
set firewall.@forwarding[-1].src='fw_game'
""","""
set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
del network.lan.ip6assign

delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname

set network.wan6.reqprefix='48'

set network.lan.type='bridge'
set network.lan.ifname='eth1'

set network.wan.type='bridge'
set network.wan6.type='bridge'
set network.wan.ifname='eth0'
set network.wan6.ifname='eth0'
"""]
            interface_config = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "10.1.1.0/29", "", "", []],
                "office":   [  20, "10.1.1.16/28", "", "", ["wan"]],
                "game":     [  30, "10.1.1.8/29", "", "", ["wan"]],
                }
            port_list = [ 'CPU', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [     0,     2,   1,  10,  20,  30, ]
            out = getconf_list_interfaces("OpenWrt", "192.168.1.0/24", interface_config, port_map, cb_vlan_ifname=cb_vlan_ifname_test1, num_wifi=2)
            self.assertEqual(expect, out)

        def test_getconf_interfaces_trunk_port2(self):
            self.maxDiff = None

            # test with trunk port
            expect = ["""
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1

set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1

set network.coredata='interface'

set network.coredata.type='bridge'
set network.coredata.ifname='eth0.10 eth2 eth4.10'

set network.coredata.proto='none'
""","""
set network.office='interface'

set network.office.type='bridge'
set network.office.ifname='eth0.20 eth3 eth4.20'

set network.office.proto='none'
""","""
set network.game='interface'

set network.game.type='bridge'
set network.game.ifname='eth0.30 eth4.30'

set network.game.proto='none'
""","""
set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
del network.lan.ip6assign

delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname

set network.wan6.reqprefix='48'

set network.lan.type='bridge'
set network.lan.ifname='eth0.1 eth1 eth4.1'

set network.wan.type='bridge'
set network.wan6.type='bridge'
set network.wan.ifname='eth0.2 eth4.2'
set network.wan6.ifname='eth0.2 eth4.2'
"""]

            interface_config = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "", "", "", []],
                "office":   [  20, "", "", "", []],
                "game":     [  30, "", "", "", []],
                }
            port_map = {
                # name: [ switch_port, device, ]
                "CPU": [ None, None ],
                "WAN": [ "eth0", "eth0" ],
                "1": [ "eth1", "eth1" ],
                "2": [ "eth2", "eth2" ],
                "3": [ "eth3", "eth3" ],
                "4": [ "eth4", "eth4" ],
            }
            def cb_vlan_ifname_test2(vlanid):
                str_port = ""
                for i in range(0,len(vlan_list)):
                    if not (port_list[i] in port_map):
                        continue
                    if not port_map[port_list[i]][0]:
                        continue
                    vlan1 = vlan_list[i]
                    if not isinstance(vlan1, list):
                        vlan1 = [ vlan_list[i] ]
                    for v in vlan1:
                        if (v == 0): # and (not (vlanid in {2})):
                            str_port += " {0}.{1}".format(port_map[port_list[i]][0], vlanid)
                        if v == vlanid:
                            str_port += " {0}".format(port_map[port_list[i]][0])
                return str_port.strip()

            port_list = [ 'CPU', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [     0,     0,   1,  10,  20,   0, ]
            out = getconf_list_interfaces("OpenWrt", "192.168.1.0/24", interface_config, port_map, cb_vlan_ifname=cb_vlan_ifname_test2, num_wifi=2)
            self.assertEqual(expect, out)



        def test_getconf_interfaces_trunk_port2_create_wan(self):
            self.maxDiff = None

            # test with trunk port
            expect = ["""
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1

set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1

set network.coredata='interface'

set network.coredata.type='bridge'
set network.coredata.ifname='eth0.10 eth2 eth4.10'

set network.coredata.proto='none'
""","""
set network.office='interface'

set network.office.type='bridge'
set network.office.ifname='eth0.20 eth3 eth4.20'

set network.office.proto='none'
""","""
set network.game='interface'

set network.game.type='bridge'
set network.game.ifname='eth0.30 eth4.30'

set network.game.proto='none'
""","""
set network.wan='interface'
set network.wan.proto='dhcp'
set network.wan6='interface'
set network.wan6.proto='dhcpv6'

set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
del network.lan.ip6assign

delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname

set network.wan6.reqprefix='48'

set network.lan.type='bridge'
set network.lan.ifname='eth0.1 eth1 eth4.1'

set network.wan.type='bridge'
set network.wan6.type='bridge'
set network.wan.ifname='eth0.2 eth4.2'
set network.wan6.ifname='eth0.2 eth4.2'
"""]
            expect2 = ["""
set wireless.@wifi-iface[-1].disabled=1
set wireless.@wifi-iface[-2].disabled=1

set wireless.@wifi-device[0].disabled=1
set wireless.@wifi-device[1].disabled=1

set network.coredata='interface'

set network.coredata.type='bridge'
set network.coredata.ifname='eth0.10 eth2 eth4.10'

set network.coredata.proto='none'
""","""
set network.office='interface'

set network.office.type='bridge'
set network.office.ifname='eth0.20 eth3 eth4.20'

set network.office.proto='none'
""","""
set network.game='interface'

set network.game.type='bridge'
set network.game.ifname='eth0.30 eth4.30'

set network.game.proto='none'
""","""
set network.wan='interface'
set network.wan.proto='dhcp'
set network.wan6='interface'
set network.wan6.proto='dhcpv6'

set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
del network.lan.ip6assign

delete dhcp.lan.ignore
delete network.lan.device
delete network.lan.type
delete network.lan.ifname
delete network.wan.device
delete network.wan.type
delete network.wan.ifname
delete network.wan6.device
delete network.wan6.type
delete network.wan6.ifname

set network.wan6.reqprefix='48'

set network.lan.type='bridge'
set network.lan.ifname='eth0.1 eth1 eth4.1'

set network.wan.type='bridge'
set network.wan6.type='bridge'
set network.wan.ifname='eth0.2 eth4.2'
set network.wan6.ifname='eth0.2 eth4.2'
"""]

            interface_config = {
                # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                "coredata": [  10, "", "", "", []],
                "office":   [  20, "", "", "", []],
                "game":     [  30, "", "", "", []],
                }
            port_map = {
                # name: [ switch_port, device, ]
                "CPU": [ None, None ],
                "WAN": [ "eth0", "eth0" ],
                "1": [ "eth1", "eth1" ],
                "2": [ "eth2", "eth2" ],
                "3": [ "eth3", "eth3" ],
                "4": [ "eth4", "eth4" ],
            }
            def cb_vlan_ifname_test2(vlanid):
                str_port = ""
                for i in range(0,len(vlan_list)):
                    if not (port_list[i] in port_map):
                        continue
                    if not port_map[port_list[i]][0]:
                        continue
                    vlan1 = vlan_list[i]
                    if not isinstance(vlan1, list):
                        vlan1 = [ vlan_list[i] ]
                    for v in vlan1:
                        if (v == 0): # and (not (vlanid in {2})):
                            str_port += " {0}.{1}".format(port_map[port_list[i]][0], vlanid)
                        if v == vlanid:
                            str_port += " {0}".format(port_map[port_list[i]][0])
                return str_port.strip()

            port_list = [ 'CPU', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [     0,     0,   1,  10,  20,   0, ]
            out = getconf_list_interfaces("OpenWrt", "192.168.1.0/24", interface_config, port_map, cb_vlan_ifname=cb_vlan_ifname_test2, num_wifi=2, create_wan=True)
            self.assertEqual(expect, out)

            out = getconf_list_interfaces("OpenWrt", "192.168.1.0/24", interface_config, port_map, cb_vlan_ifname=cb_vlan_ifname_test2, num_wifi=2, create_wan=True, has_subnet_ips=False)
            self.assertEqual(expect2, out)

        def test_getconf_default_network(self):
            self.maxDiff = None

            exp = """uci batch << EOF

# Default Network
set network.globals='globals'
set network.globals.ula_prefix='fd35:f963:a3ba::/48'

# loopback
set network.loopback='interface'
set network.loopback.ifname='lo'
set network.loopback.proto='static'
set network.loopback.ipaddr='127.0.0.1'
set network.loopback.netmask='255.0.0.0'

# Interface lan on ifname eth1 eth2 eth3 eth4
set network.lan='interface'
set network.lan.type='bridge'
set network.lan.ifname='eth1 eth2 eth3 eth4'
set network.lan.ip6assign='60'
set network.lan.proto='static'
set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'

set dhcp.lan='dhcp'
set dhcp.lan.interface='lan'
set dhcp.lan.leasetime='12h'
set dhcp.lan.start='100'
set dhcp.lan.limit='150'
set dhcp.lan.ra_management='1'
set dhcp.lan.dhcpv4='server'
set dhcp.lan.dhcpv6='server'
set dhcp.lan.ra='server'

# Interface wan on ifname eth0
set network.wan='interface'
set network.wan.type='bridge'
set network.wan.ifname='eth0'
set network.wan.proto='dhcp'

# Configure DNS provider
set network.wan.peerdns="1"
#set network.wan.dns="8.8.8.8 8.8.4.4"
set network.wan6.peerdns="1"
#set network.wan6.dns="2001:4860:4860::8888 2001:4860:4860::8844"

set network.wan6='interface'
set network.wan6.type='bridge'
set network.wan6.ifname='eth0'
set network.wan6.proto='dhcpv6'

set dhcp.wan='dhcp'
set dhcp.wan.interface='wan'
set dhcp.wan.ignore='1'

add dhcp dnsmasq
set dhcp.@dnsmasq[0]=dnsmasq
set dhcp.@dnsmasq[0].domainneeded='1'
set dhcp.@dnsmasq[0].boguspriv='1'
set dhcp.@dnsmasq[0].filterwin2k='0'
set dhcp.@dnsmasq[0].localise_queries='1'
set dhcp.@dnsmasq[0].rebind_protection='1'
set dhcp.@dnsmasq[0].rebind_localhost='1'
set dhcp.@dnsmasq[0].local='/lan/'
set dhcp.@dnsmasq[0].domain='lan'
set dhcp.@dnsmasq[0].expandhosts='1'
set dhcp.@dnsmasq[0].nonegcache='0'
set dhcp.@dnsmasq[0].authoritative='1'
set dhcp.@dnsmasq[0].readethers='1'
set dhcp.@dnsmasq[0].leasefile='/tmp/dhcp.leases'
set dhcp.@dnsmasq[0].nonwildcard='1'
set dhcp.@dnsmasq[0].localservice='1'
# set default DNS
del dhcp.@dnsmasq[0].server
add_list dhcp.@dnsmasq[0].server='8.8.8.8'
add_list dhcp.@dnsmasq[0].server='8.8.4.4'

set dhcp.odhcpd='odhcpd'
set dhcp.odhcpd.maindhcp='0'
set dhcp.odhcpd.leasefile='/tmp/hosts/odhcpd'
set dhcp.odhcpd.leasetrigger='/usr/sbin/odhcpd-update'
set dhcp.odhcpd.loglevel='4'

add firewall defaults
set firewall.@defaults[0].syn_flood='1'
set firewall.@defaults[0].input='ACCEPT'
set firewall.@defaults[0].output='ACCEPT'
set firewall.@defaults[0].forward='REJECT'
#set firewall.@defaults[0].disable_ipv6='1'

add firewall zone
set firewall.@zone[-1].name=lan
set firewall.@zone[-1].network='lan'
set firewall.@zone[-1].input=ACCEPT
set firewall.@zone[-1].output=ACCEPT
set firewall.@zone[-1].forward=ACCEPT

add firewall zone
set firewall.@zone[-1].name=wan
set firewall.@zone[-1].network='wan wan6'
set firewall.@zone[-1].input=REJECT
set firewall.@zone[-1].output=ACCEPT
set firewall.@zone[-1].forward=REJECT
set firewall.@zone[-1].masq=1
set firewall.@zone[-1].mtu_fix=1

add firewall forwarding
set firewall.@forwarding[-1].src=lan
set firewall.@forwarding[-1].dest=wan

add firewall rule
set firewall.@rule[-1].name='Allow-DHCP-Renew'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='udp'
set firewall.@rule[-1].dest_port='68'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv4'

add firewall rule
set firewall.@rule[-1].name='Allow-Ping'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='icmp'
set firewall.@rule[-1].icmp_type='echo-request'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv4'

add firewall rule
set firewall.@rule[-1].name='Allow-IGMP'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='igmp'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv4'

add firewall rule
set firewall.@rule[-1].name='Allow-DHCPv6'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='udp'
set firewall.@rule[-1].src_ip='fc00::/6'
set firewall.@rule[-1].dest_ip='fc00::/6'
set firewall.@rule[-1].dest_port='546'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-MLD'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='icmp'
set firewall.@rule[-1].src_ip='fe80::/10'
#delete firewall.@rule[-1].icmp_type
add_list firewall.@rule[-1].icmp_type='130/0'
add_list firewall.@rule[-1].icmp_type='131/0'
add_list firewall.@rule[-1].icmp_type='132/0'
add_list firewall.@rule[-1].icmp_type='143/0'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-ICMPv6-Input'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].proto='icmp'
#delete firewall.@rule[-1].icmp_type
add_list firewall.@rule[-1].icmp_type='echo-request'
add_list firewall.@rule[-1].icmp_type='echo-reply'
add_list firewall.@rule[-1].icmp_type='destination-unreachable'
add_list firewall.@rule[-1].icmp_type='packet-too-big'
add_list firewall.@rule[-1].icmp_type='time-exceeded'
add_list firewall.@rule[-1].icmp_type='bad-header'
add_list firewall.@rule[-1].icmp_type='unknown-header-type'
add_list firewall.@rule[-1].icmp_type='router-solicitation'
add_list firewall.@rule[-1].icmp_type='neighbour-solicitation'
add_list firewall.@rule[-1].icmp_type='router-advertisement'
add_list firewall.@rule[-1].icmp_type='neighbour-advertisement'
set firewall.@rule[-1].limit='1000/sec'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-ICMPv6-Forward'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].dest='*'
set firewall.@rule[-1].proto='icmp'
#delete firewall.@rule[-1].icmp_type
add_list firewall.@rule[-1].icmp_type='echo-request'
add_list firewall.@rule[-1].icmp_type='echo-reply'
add_list firewall.@rule[-1].icmp_type='destination-unreachable'
add_list firewall.@rule[-1].icmp_type='packet-too-big'
add_list firewall.@rule[-1].icmp_type='time-exceeded'
add_list firewall.@rule[-1].icmp_type='bad-header'
add_list firewall.@rule[-1].icmp_type='unknown-header-type'
set firewall.@rule[-1].limit='1000/sec'
set firewall.@rule[-1].target='ACCEPT'
set firewall.@rule[-1].family='ipv6'

add firewall rule
set firewall.@rule[-1].name='Allow-IPSec-ESP'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].dest='lan'
set firewall.@rule[-1].proto='esp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='Allow-ISAKMP'
set firewall.@rule[-1].src='wan'
set firewall.@rule[-1].dest='lan'
set firewall.@rule[-1].dest_port='500'
set firewall.@rule[-1].proto='udp'
set firewall.@rule[-1].target='ACCEPT'

add firewall include
set firewall.@include[-1].path='/etc/firewall.user'

add system system
set system.@system[-1].hostname='OpenWrt'
set system.@system[-1].timezone='UTC'
set system.@system[-1].ttylogin='0'
set system.@system[-1].log_size='64'
set system.@system[-1].urandom_seed='0'

set system.ntp='timeserver'
set system.ntp.enabled='1'
set system.ntp.enable_server='0'
#delete system.ntp.server
add_list system.ntp.server='0.openwrt.pool.ntp.org'
add_list system.ntp.server='1.openwrt.pool.ntp.org'
add_list system.ntp.server='2.openwrt.pool.ntp.org'
add_list system.ntp.server='3.openwrt.pool.ntp.org'
set dhcp.@dnsmasq[0].resolvfile='/tmp/resolv.conf.d/resolv.conf.auto'
commit
EOF
"""

            port_map_gns3_openwrt = {
                'CPU': [ None, None ],
                'WAN': [ 'eth0', 'eth0' ],
                '1': [ 'eth1', 'eth1' ],
                '2': [ 'eth2', 'eth2' ],
                '3': [ 'eth3', 'eth3' ],
                '4': [ 'eth4', 'eth4' ],
            }
            port_map = port_map_gns3_openwrt

            port_list = sorted(port_map)
            vlan_list = [1 for i in range(0,len(port_list))]
            for i in range(0,len(vlan_list)):
                if port_list[i] == 'CPU':
                    vlan_list[i] = 0
                elif port_list[i] == 'WAN':
                    vlan_list[i] = 2

            self.assertEqual({i for i in port_list}, { 'CPU', 'WAN','1','2','3','4', })
            for i in range(0,len(port_list)):
                if port_list[i] == 'CPU':
                    self.assertEqual(vlan_list[i], 0)
                elif port_list[i] == 'WAN':
                    self.assertEqual(vlan_list[i], 2)
                else:
                    self.assertEqual(vlan_list[i], 1)

            ifname_gen = VlanPortGenerator(port_map, port_list, vlan_list)

            def cb_vlan_ifname1(vlanid):
                return ifname_gen.get_port_list_ifname(vlanid)
            cb_vlan_ifname = None
            if not None == ifname_gen:
                cb_vlan_ifname = cb_vlan_ifname1

            #L.info("setup default network ...")
            cmd_intf = getconf_default_network(cb_vlan_ifname)
            #L.info("default net cmd={0}".format(cmd_intf))
            self.assertEqual(cmd_intf, exp)


        def test_vlan_list_gen_x86_1(self):
            port_map = {
                'CPU': [ None, None ],
                'WAN': [ 'eth0', 'eth0' ],
                '1': [ 'eth1', 'eth1' ],
                '2': [ 'eth2', 'eth2' ],
                '3': [ 'eth3', 'eth3' ],
                '4': [ 'eth4', 'eth4' ],
            }
            port_list = [ 'CPU', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [     0,     2,   1,  10,  10,  10, ]
            gen = VlanPortGenerator(port_map, port_list, vlan_list)

            self.assertEqual(gen.get_port_list_ifname(vlanid=10), "eth2 eth3 eth4")
            self.assertEqual(gen.get_port_list_ifname(vlanid= 2), "eth0")
            self.assertEqual(gen.get_port_list_ifname(vlanid= 1), "eth1")

        def test_vlan_list_gen_x86_2(self):
            port_map = {
                'CPU': [ None, None ],
                'WAN': [ 'eth0', 'eth0' ],
                '1': [ 'eth1', 'eth1' ],
                '2': [ 'eth2', 'eth2' ],
                '3': [ 'eth3', 'eth3' ],
                '4': [ 'eth4', 'eth4' ],
            }
            port_list = [ 'CPU', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [     0,     0,   1,  10,  10,  10, ]
            gen = VlanPortGenerator(port_map, port_list, vlan_list)

            self.assertEqual(gen.get_port_list_ifname(vlanid=10), "eth0.10 eth2 eth3 eth4")
            self.assertEqual(gen.get_port_list_ifname(vlanid= 2), "")
            self.assertEqual(gen.get_port_list_ifname(vlanid= 1), "eth1")

        def test_vlan_list_gen2(self):
            port_map = { 'CPU': [0, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
            port_list = ['CPU', 'WAN', '1','2','3','4', ]
            vlan_list = [    0,     2,   1, 30, 20, 50, ]
            gen = VlanPortGenerator(port_map, port_list, vlan_list)

            self.assertEqual(gen.get_port_list_vlan(vlanid=30), "0t 3")
            self.assertEqual(gen.get_port_list_vlan(vlanid= 2), "0t 1")
            self.assertEqual(gen.get_port_list_vlan(vlanid= 1), "0t 2")

        def test_vlan_list_gen3(self):
            port_map = { 'CPU': [0, 'eth0'], 'CPU2': [6, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
            port_list = ['CPU', 'CPU2', 'WAN', '1','2','3','4', ]
            vlan_list = [    0,   0,  2,   1, 30, 20, 50, ]
            gen = VlanPortGenerator(port_map, port_list, vlan_list)

            self.assertEqual(gen.get_port_list_vlan(vlanid=50), "0t 5")
            self.assertEqual(gen.get_port_list_vlan(vlanid=30), "0t 3")
            self.assertEqual(gen.get_port_list_vlan(vlanid= 2), "6t 1")
            self.assertEqual(gen.get_port_list_vlan(vlanid= 1), "0t 2")

        def test_vlan_list_gen4(self):
            port_map = { 'CPU': [0, 'eth0'], 'CPU2': [6, 'eth0'], 'WAN': [1, 'eth0'], '1': [2, 'eth0'], '2': [3, 'eth0'], '3': [4, 'eth0'], '4': [5, 'eth0'] }
            port_list = ['CPU', 'CPU2', 'WAN', '1', '2', '3', '4', ]
            vlan_list = [    0,      0,     2,   1,  80,  20,   1, ]
            gen = VlanPortGenerator(port_map, port_list, vlan_list)

            self.assertEqual(gen.get_port_list_vlan(vlanid=20), "0t 4")
            self.assertEqual(gen.get_port_list_vlan(vlanid=80), "0t 3")
            self.assertEqual(gen.get_port_list_vlan(vlanid= 2), "6t 1")
            self.assertEqual(gen.get_port_list_vlan(vlanid= 1), "0t 2 5")

        def test_parse_board_line(self):
            input="""get_board_begin
tplink,archer-c7-v2
get_board_end
"""
            self.assertEqual(parse_board_line(input), 'tplink,archer-c7-v2')
            self.assertEqual(parse_board_line(input.replace(",", "_")), 'tplink_archer-c7-v2')

        def test_parse_target(self):
            input = """get_target_begin
DISTRIB_TARGET='ath79/generic'
get_target_end
"""
            self.assertEqual(parse_target(input), 'ath79/generic')

        def test_parse_version(self):
            input = """get_version_begin
DISTRIB_RELEASE='SNAPSHOT'
DISTRIB_REVISION='r15475-c625c821d1'
get_version_end
"""
            self.assertEqual(parse_version(input), 'r15475-c625c821d1')

            input="""get_version_begin
DISTRIB_RELEASE='19.07.5'
DISTRIB_REVISION='r11257-5090152ae3'
get_version_end
"""
            self.assertEqual(parse_version(input), '19.07.5')

        def test_parse_model_line(self):
            input="""get_model_begin
QEMU Standard PC (i440FX + PIIX, 1996)
get_model_end
"""
            self.assertEqual(parse_model_line(input), 'QEMU Standard PC (i440FX + PIIX, 1996)')

            input="""get_model_begin
TP-Link Archer C6 v2 (US) / A6 v2 (US/TW)
get_model_end
"""
            self.assertEqual(parse_model_line(input), 'TP-Link Archer C6 v2 (US) / A6 v2 (US/TW)')

        def test_parse_hostname(self):
            input="""get_hostname_begin
system.@system[0].hostname='homemain-gns3'
get_hostname_end
"""
            self.assertEqual(parse_hostname(input), 'homemain-gns3')


        # example:
        #   swconfig list
        #   Found: switch0 - rtl8367
        #   /bin/ash: swconfig: not found
        def test_parse_swconfig_line(self):
            input="""get_swconfig_begin
Found: switch0 - rtl8367
get_swconfig_end
"""
            self.assertEqual(parse_swconfig_line(input), ['switch0', 'rtl8367'])

            input="""onfig list


Found: switch0 - rtl8367
"""
            self.assertEqual(parse_swconfig_line(input), ['switch0', 'rtl8367'])


            input="""onfig list


Found: switch0 - mdio.0
"""
            self.assertEqual(parse_swconfig_line(input), ['switch0', 'mdio.0'])


            input="""swconfig list
Found: switch0 - eth0
"""
            self.assertEqual(parse_swconfig_line(input), ['switch0', 'eth0'])


            input="""get_swconfig_begin
/bin/ash: swconfig: not found
get_swconfig_end
"""
            self.assertEqual(parse_swconfig_line(input), None)


        def test_parse_swconfig_support_vid_line_asus(self):

            # Asus RT-N56U
            input="""swconfig dev switch0 help
switch0: rtl8367(RTL8367), ports: 10 (cpu @ 9), vlans: 4096
     --switch
        Attribute 1 (int): enable_vlan (Enable VLAN mode)
        Attribute 2 (int): enable_vlan4k (Enable VLAN 4K mode)
        Attribute 3 (none): reset_mibs (Reset all MIB counters)
        Attribute 4 (int): max_length (Get/Set the maximum length of valid packets(0:1522, 1:1536, 2:1552, 3:16000))
        Attribute 5 (none): apply (Activate changes in the hardware)
        Attribute 6 (none): reset (Reset the switch)
     --vlan
        Attribute 1 (string): info (Get vlan information)
        Attribute 2 (int): fid (Get/Set vlan FID)
        Attribute 3 (ports): ports (VLAN port mapping)
     --port
        Attribute 1 (none): reset_mib (Reset single port MIB counters)
        Attribute 2 (string): mib (Get MIB counters for port)
        Attribute 3 (int): pvid (Primary VLAN ID)
        Attribute 4 (unknown): link (Get port link information)
"""
            self.assertEqual(parse_swconfig_support_vid_line(input), False)
            self.assertEqual(parse_swconfig_support_vlan4k_line(input), True)

        def test_parse_swconfig_support_vid_line_tplink1(self):

            # TP-Link Archer C6 v2 (US) / A6 v2 (US/TW)
            input="""swconfig dev switch0 help
switch0: mdio.0(Atheros AR8337), ports: 7 (cpu @ 0), vlans: 4096
     --switch
	Attribute 1 (int): enable_vlan (Enable VLAN mode)
	Attribute 2 (none): reset_mibs (Reset all MIB counters)
	Attribute 3 (int): ar8xxx_mib_poll_interval (MIB polling interval in msecs (0 to disable))
	Attribute 4 (int): ar8xxx_mib_type (MIB type (0=basic 1=extended))
	Attribute 5 (int): enable_mirror_rx (Enable mirroring of RX packets)
	Attribute 6 (int): enable_mirror_tx (Enable mirroring of TX packets)
	Attribute 7 (int): mirror_monitor_port (Mirror monitor port)
	Attribute 8 (int): mirror_source_port (Mirror source port)
	Attribute 9 (int): arl_age_time (ARL age time (secs))
	Attribute 10 (string): arl_table (Get ARL table)
	Attribute 11 (none): flush_arl_table (Flush ARL table)
	Attribute 12 (int): igmp_snooping (Enable IGMP Snooping)
	Attribute 13 (int): igmp_v3 (Enable IGMPv3 support)
	Attribute 14 (none): apply (Activate changes in the hardware)
	Attribute 15 (none): reset (Reset the switch)
     --vlan
	Attribute 1 (int): vid (VLAN ID (0-4094))
	Attribute 2 (ports): ports (VLAN port mapping)
     --port
	Attribute 1 (none): reset_mib (Reset single port MIB counters)
	Attribute 2 (string): mib (Get port's MIB counters)
	Attribute 3 (int): enable_eee (Enable EEE PHY sleep mode)
	Attribute 4 (none): flush_arl_table (Flush port's ARL table entries)
	Attribute 5 (int): igmp_snooping (Enable port's IGMP Snooping)
	Attribute 6 (int): vlan_prio (Port VLAN default priority (VLAN PCP) (0-7))
	Attribute 7 (int): pvid (Primary VLAN ID)
	Attribute 8 (unknown): link (Get port link information)
"""
            self.assertEqual(parse_swconfig_support_vid_line(input), True)
            self.assertEqual(parse_swconfig_support_vlan4k_line(input), False)

        def test_parse_swconfig_support_vid_line_tplink2(self):
            # TP-Link Archer C7 v2
            input="""
switch0: mdio-bus.0(Atheros AR8327), ports: 7 (cpu @ 0), vlans: 4096
     --switch
	Attribute 1 (int): enable_vlan (Enable VLAN mode)
	Attribute 2 (none): reset_mibs (Reset all MIB counters)
	Attribute 3 (int): ar8xxx_mib_poll_interval (MIB polling interval in msecs (0 to disable))
	Attribute 4 (int): ar8xxx_mib_type (MIB type (0=basic 1=extended))
	Attribute 5 (int): enable_mirror_rx (Enable mirroring of RX packets)
	Attribute 6 (int): enable_mirror_tx (Enable mirroring of TX packets)
	Attribute 7 (int): mirror_monitor_port (Mirror monitor port)
	Attribute 8 (int): mirror_source_port (Mirror source port)
	Attribute 9 (int): arl_age_time (ARL age time (secs))
	Attribute 10 (string): arl_table (Get ARL table)
	Attribute 11 (none): flush_arl_table (Flush ARL table)
	Attribute 12 (int): igmp_snooping (Enable IGMP Snooping)
	Attribute 13 (int): igmp_v3 (Enable IGMPv3 support)
	Attribute 14 (none): apply (Activate changes in the hardware)
	Attribute 15 (none): reset (Reset the switch)
     --vlan
	Attribute 1 (int): vid (VLAN ID (0-4094))
	Attribute 2 (ports): ports (VLAN port mapping)
     --port
	Attribute 1 (none): reset_mib (Reset single port MIB counters)
	Attribute 2 (string): mib (Get port's MIB counters)
	Attribute 3 (int): enable_eee (Enable EEE PHY sleep mode)
	Attribute 4 (none): flush_arl_table (Flush port's ARL table entries)
	Attribute 5 (int): igmp_snooping (Enable port's IGMP Snooping)
	Attribute 6 (int): vlan_prio (Port VLAN default priority (VLAN PCP) (0-7))
	Attribute 7 (int): pvid (Primary VLAN ID)
	Attribute 8 (unknown): link (Get port link information)
"""
            self.assertEqual(parse_swconfig_support_vid_line(input), True)
            self.assertEqual(parse_swconfig_support_vlan4k_line(input), False)


        def test_re1(self):
            line = """Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.

root@OpenWrt:/# 
root@OpenWrt:/# cat /tmp/sysinfo/model ; echo "get_model_""end"
QEMU Standard PC (i440FX + PIIX, 1996)
"""
            import re
            #L.info("match='{0}'".format( re.search('\s(.*)\s$', line).group(0).strip() ))
            self.assertEqual(re.search('\s(.*)\s$', line).group(0).strip(), 'QEMU Standard PC (i440FX + PIIX, 1996)')


        def test_set(self):
            list1 = [0,10,20,30,40,50]
            exp1 = {1,2,10,20,30,40,50}
            #set1 = {1,2}.union({ list1[i] for i in range(0,len(list1)) })
            #self.assertEqual(set1, exp1)
            #set1 = {1,2}.union({ (list1 > 0) })
            #self.assertEqual(set1, exp1)
            set1 = {1,2}.union({ list1[i] for i in range(0,len(list1)) })
            set1.remove(0)
            self.assertEqual(set1, exp1)

        def test_getconf_default_vlan_swconfig(self):
            self.maxDiff = None
            port_map = {
                'CPU': [ 0, 'eth0' ],
                'WAN': [ 1, 'eth0' ],
                '1': [ 2, 'eth0' ],
                '2': [ 3, 'eth0' ],
                '3': [ 4, 'eth0' ],
                '4': [ 5, 'eth0' ],
            }
            exp = """uci batch << EOF
# Default VLANs
add network switch
set network.@switch[-1].name=switch0
set network.@switch[-1].reset=1
set network.@switch[-1].enable_vlan=1
commit
EOF
uci batch << EOF
# VLAN1=1 at HW port 0t 2 3 4 5
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='1'
set network.@switch_vlan[-1].vid='1'
set network.@switch_vlan[-1].ports='0t 2 3 4 5'

# VLAN2=2 at HW port 0t 1
add network switch_vlan
set network.@switch_vlan[-1].device='switch0'
set network.@switch_vlan[-1].vlan='2'
set network.@switch_vlan[-1].vid='2'
set network.@switch_vlan[-1].ports='0t 1'
commit
EOF
"""
            out = getconf_default_vlan_swconfig(port_map)
            self.assertEqual(out, exp)

        def test_detect_hw_wifi_num(self):
            input = """root@netlab1:~# iw dev
phy#1
	Interface wlan1-4
		ifindex 90
		wdev 0x100000027
		addr 66:ff:62:8f:9b:ab
		ssid CherryGuest
		type AP
		channel 11 (2462 MHz), width: 20 MHz, center1: 2462 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	109	0	0	0	0	25467		110
	Interface wlan1-3
		ifindex 88
		wdev 0x100000026
		addr 62:ff:62:8f:9b:ab
		ssid Chalk
		type AP
		channel 11 (2462 MHz), width: 20 MHz, center1: 2462 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	0	0	0	0	0	0		0
	Interface wlan1-2
		ifindex 87
		wdev 0x100000025
		addr 6e:ff:62:8f:9b:ab
		ssid Cherry
		type AP
		channel 11 (2462 MHz), width: 20 MHz, center1: 2462 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	262	0	0	0	0	29052		268
	Interface wlan1-1
		ifindex 86
		wdev 0x100000024
		addr 6a:ff:62:8f:9b:ab
		ssid Coal
		type AP
		channel 11 (2462 MHz), width: 20 MHz, center1: 2462 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	31	0	0	0	0	31338		51
	Interface wlan1
		ifindex 85
		wdev 0x100000023
		addr 68:ff:62:8f:9b:ab
		ssid Slat
		type AP
		channel 11 (2462 MHz), width: 20 MHz, center1: 2462 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	366	0	0	0	0	74294		374
phy#0
	Interface wlan0-4
		ifindex 94
		wdev 0x15
		addr 66:ff:62:8f:9b:aa
		ssid CherryGuest
		type AP
		channel 36 (5180 MHz), width: 80 MHz, center1: 5210 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	4000	0	0	0	0	604593		4000
	Interface wlan0-3
		ifindex 93
		wdev 0x14
		addr 62:ff:62:8f:9b:aa
		ssid Tourmaline
		type AP
		channel 36 (5180 MHz), width: 80 MHz, center1: 5210 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	0	0	0	0	0	0		0
	Interface wlan0-2
		ifindex 92
		wdev 0x13
		addr 6e:ff:62:8f:9b:aa
		ssid Cherry
		type AP
		channel 36 (5180 MHz), width: 80 MHz, center1: 5210 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	9	0	0	0	0	1106		9
	Interface wlan0-1
		ifindex 91
		wdev 0x12
		addr 6a:ff:62:8f:9b:aa
		ssid Coal
		type AP
		channel 36 (5180 MHz), width: 80 MHz, center1: 5210 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	0	0	0	0	0	0		0
	Interface wlan0
		ifindex 89
		wdev 0x11
		addr 68:ff:62:8f:9b:aa
		ssid Slat
		type AP
		channel 36 (5180 MHz), width: 80 MHz, center1: 5210 MHz
		txpower 20.00 dBm
		multicast TXQ:
			qsz-byt	qsz-pkt	flows	drops	marks	overlmt	hashcol	tx-bytes	tx-packets
			0	0	0	0	0	0	0	0		0
"""

            self.assertEqual(2, get_hw_wifi_number(input))

        def test_getconf_dns_server(self):
            self.maxDiff = None

            myparam = {
                "name": "DNS server, ip-hole",
                "prefix": "pihole_",
                "ip": "192.168.101.24",
                "zone_server": "office",
                "zones_from": [ "office", "game", "guest" ],
            }
            exp = """uci batch << EOF
add_list dhcp.office.dhcp_option='6,192.168.101.24'
add_list dhcp.game.dhcp_option='6,192.168.101.24'
add_list dhcp.guest.dhcp_option='6,192.168.101.24'
commit
EOF
"""
            ret = getconf_dns_server(param = myparam)
            #print(f"return string = \n{ret}")
            self.assertEqual(ret, exp)

        def test_getconf_wan_port(self):
            self.maxDiff = None

            myparam = {
                "name": "Web server",
                "port": 80, # external port
                "zone_server": "office",
                "ip": "192.168.101.24", # internal host IP
                "protocol": [ "tcp", ],
                "dest_port": 81 # internal host port
            }
            exp = """uci batch << EOF
add firewall redirect
set firewall.@redirect[-1].target='DNAT'
set firewall.@redirect[-1].name='Web server'
set firewall.@redirect[-1].src='wan'
set firewall.@redirect[-1].src_dport='80'
set firewall.@redirect[-1].dest_ip='192.168.101.24'
set firewall.@redirect[-1].dest_port='81'
set firewall.@redirect[-1].reflection='1'
add_list firewall.@redirect[-1].proto='tcp'
commit
EOF
"""
            ret = getconf_wan_port(param = myparam)
            #print(f"return string = \n{ret}")
            self.assertEqual(ret, exp)

            myparam = {
                "name": "Web server SSL",
                "port": 443, # external port
                "zone_server": "office",
                "ip": "192.168.101.24", # internal host IP
                "protocol": [ "tcp", "udp" ],
                "dest_port": 2443 # internal host port
            }
            exp = """uci batch << EOF
add firewall redirect
set firewall.@redirect[-1].target='DNAT'
set firewall.@redirect[-1].name='Web server SSL'
set firewall.@redirect[-1].src='wan'
set firewall.@redirect[-1].src_dport='443'
set firewall.@redirect[-1].dest_ip='192.168.101.24'
set firewall.@redirect[-1].dest_port='2443'
set firewall.@redirect[-1].reflection='1'
add_list firewall.@redirect[-1].proto='tcp'
add_list firewall.@redirect[-1].proto='udp'
commit
EOF
"""
            ret = getconf_wan_port(param = myparam)
            #print(f"return string = \n{ret}")
            self.assertEqual(ret, exp)

        def test_getconf_access_server(self):
            self.maxDiff = None

            myparam = {
                "name": "Samba server 1",
                "prefix": "fileserver_",
                "zone_server": "office",
                "ip": "10.1.1.24",
                "zones_from": ["office", "game", "noinet", "wificli", "netlab", "iotlab", "guest"],
                "dest_port": "22 69 80 443 111 137 138 139 445 9091 4711 59000-59499",
            }
            exp = """uci batch << EOF

add firewall rule
set firewall.@rule[-1].name='fileserver_game'
set firewall.@rule[-1].src='fw_game'
set firewall.@rule[-1].dest='fw_office'
set firewall.@rule[-1].dest_ip='10.1.1.24'
set firewall.@rule[-1].dest_port='22 69 80 443 111 137 138 139 445 9091 4711 59000-59499'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='fileserver_noinet'
set firewall.@rule[-1].src='fw_noinet'
set firewall.@rule[-1].dest='fw_office'
set firewall.@rule[-1].dest_ip='10.1.1.24'
set firewall.@rule[-1].dest_port='22 69 80 443 111 137 138 139 445 9091 4711 59000-59499'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='fileserver_wificli'
set firewall.@rule[-1].src='fw_wificli'
set firewall.@rule[-1].dest='fw_office'
set firewall.@rule[-1].dest_ip='10.1.1.24'
set firewall.@rule[-1].dest_port='22 69 80 443 111 137 138 139 445 9091 4711 59000-59499'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='fileserver_netlab'
set firewall.@rule[-1].src='fw_netlab'
set firewall.@rule[-1].dest='fw_office'
set firewall.@rule[-1].dest_ip='10.1.1.24'
set firewall.@rule[-1].dest_port='22 69 80 443 111 137 138 139 445 9091 4711 59000-59499'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='fileserver_iotlab'
set firewall.@rule[-1].src='fw_iotlab'
set firewall.@rule[-1].dest='fw_office'
set firewall.@rule[-1].dest_ip='10.1.1.24'
set firewall.@rule[-1].dest_port='22 69 80 443 111 137 138 139 445 9091 4711 59000-59499'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='fileserver_guest'
set firewall.@rule[-1].src='fw_guest'
set firewall.@rule[-1].dest='fw_office'
set firewall.@rule[-1].dest_ip='10.1.1.24'
set firewall.@rule[-1].dest_port='22 69 80 443 111 137 138 139 445 9091 4711 59000-59499'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'
commit
EOF
"""
            ret = getconf_access_server(param = myparam)
            #print(f"return string = \n{ret}")
            self.assertEqual(ret, exp)
            myparam = {
                "name": "Printer server 1",
                "prefix": "printserver_",
                "zone_server": "inetsvr",
                "ip": "10.1.1.3",
                "zones_from": [ "wificli", "netlab", "guest" ],
                "dest_port": "515 631 9100 3702",
            }
            exp = """uci batch << EOF

add firewall rule
set firewall.@rule[-1].name='printserver_wificli'
set firewall.@rule[-1].src='fw_wificli'
set firewall.@rule[-1].dest='fw_inetsvr'
set firewall.@rule[-1].dest_ip='10.1.1.3'
set firewall.@rule[-1].dest_port='515 631 9100 3702'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='printserver_netlab'
set firewall.@rule[-1].src='fw_netlab'
set firewall.@rule[-1].dest='fw_inetsvr'
set firewall.@rule[-1].dest_ip='10.1.1.3'
set firewall.@rule[-1].dest_port='515 631 9100 3702'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'

add firewall rule
set firewall.@rule[-1].name='printserver_guest'
set firewall.@rule[-1].src='fw_guest'
set firewall.@rule[-1].dest='fw_inetsvr'
set firewall.@rule[-1].dest_ip='10.1.1.3'
set firewall.@rule[-1].dest_port='515 631 9100 3702'
set firewall.@rule[-1].proto='tcp udp icmp'
set firewall.@rule[-1].target='ACCEPT'
commit
EOF
"""
            ret = getconf_access_server(param = myparam)
            #print(f"return string = \n{ret}")
            self.assertEqual(ret, exp)

        def test_port_vlan_to_port_list(self):
            myparam = {
                "arg_port_vlan": {
                    "CPU":  0,
                    "WAN":  2,
                    "1":  1,
                    "2": 80,
                    "3": 20,
                    "4":  0,
                "CPU2":  0,
                },
                "arg_port_list": [  "CPU", "CPU2", "WAN", "1", "2", "3", "4", ],
                "arg_vlan_list": [     0,      0,     0,   1,  80,  20,   1, ],
            }
            port_vlan = myparam['arg_port_vlan']

            port_list = sorted(port_vlan)
            vlan_list = [port_vlan[i] for i in port_list]
            #print(f"port_list={port_list}")
            #print(f"vlan_list={vlan_list}")
            for i in range(len(port_list)):
                self.assertEqual(port_vlan[port_list[i]], vlan_list[i])

        def xtest_getconf_set_network(self):
            exp = """set network.loopback.ipaddr='127.0.0.1'
set network.loopback.netmask='255.0.0.0'
"""
            ipnet = get_network_addr('127.0.0.0/8')
            self.assertNotEqual(ipnet, None)
            cmd_intf = getconf_set_network(ipnet, 'loopback')
            self.assertEqual(cmd_intf, exp)

            exp = """set network.lan.ipaddr='192.168.1.1'
set network.lan.netmask='255.255.255.0'
"""
            ipnet = get_network_addr('192.168.1.0/24')
            self.assertNotEqual(ipnet, None)
            cmd_intf = getconf_set_network(ipnet, 'lan')
            self.assertEqual(cmd_intf, exp)

        def test_getconf_set_ipv4_24_range(self):
            exp = """set dhcp.myint.start='98'
set dhcp.myint.limit='30'
"""
            ipnet = get_network_addr('10.1.1.96/27')
            self.assertNotEqual(ipnet, None)
            cmd_intf = getconf_set_ipv4_24_range(ipnet, 'myint')
            self.assertEqual(cmd_intf, exp)

        def test_getconf_vlan_dsa0(self):
            self.maxDiff = None
            exp1_1 = """add network device
set network.@device[-1].name='br-lan'
set network.@device[-1].type='bridge'
add_list network.@device[-1].ports=lan1
add_list network.@device[-1].ports=lan2
add_list network.@device[-1].ports=lan3
add_list network.@device[-1].ports=lan4
"""

            exp1_2 = """# bridge-vlan

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='1'
add_list network.@bridge-vlan[-1].ports='lan1:u*'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='10'
add_list network.@bridge-vlan[-1].ports='lan4:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='20'
add_list network.@bridge-vlan[-1].ports='lan3:u*'
add_list network.@bridge-vlan[-1].ports='lan4:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='30'
add_list network.@bridge-vlan[-1].ports='lan4:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='80'
add_list network.@bridge-vlan[-1].ports='lan2:u*'
add_list network.@bridge-vlan[-1].ports='lan4:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='100'
add_list network.@bridge-vlan[-1].ports='lan4:t'

"""

            myparam = {
                "arg_interface_config": {
                    # name: [vlan, ip/bit, wifi, wifi pw, [list of forward zone]]
                    "coredata": [  10, "10.1.1.0/29", "", "", []],
                    "office":   [  20, "10.1.1.16/28", "", "", ["wan"]],
                    "game":     [  30, "10.1.1.8/29", "", "", ["wan"]],
                    "untrust":  [  80, "10.1.1.56/29", "", "", ["wan"]],
                    "netlab":   [ 100, "10.1.3.0/24", "", "", ["wan"]],
                },
                "arg_port_map": {
                    'WAN': [ 'wan', 'eth0' ],
                    '1': [ 'lan1', 'eth0' ],
                    '2': [ 'lan2', 'eth0' ],
                    '3': [ 'lan3', 'eth0' ],
                    '4': [ 'lan4', 'eth0' ],
                },
                "arg_port_vlan": {
                    "1":  1,
                    "2": 80,
                    "3": 20,
                    "4":  0,
                },
            }
            interface_config = myparam['arg_interface_config']
            port_map = myparam['arg_port_map']

            port_vlan = myparam['arg_port_vlan']
            [port_list, vlan_list] = port_vlan_to_lists(port_vlan)
            #print(f"port_vlan={port_vlan}")
            #print(f"port_list={port_list}")
            #print(f"vlan_list={vlan_list}")

            vlan_set = { interface_config[i][0] for i in interface_config }
            vlan_set1 = vlan_set.union({ port_vlan[i] for i in port_vlan })
            vlan_set1.remove(0)
            vlan_list2 = list(vlan_set1)
            vlan_list2.sort()
            set1 = vlan_set.union({ i for i in vlan_list2 })
            self.assertEqual(set1, {1,10,20,30,80,100})

            #print(f"port_vlan2={port_vlan}")
            #print(f"port_list2={port_list}")
            #print(f"vlan_list2={vlan_list}")
            conf = _getconf_trunk_bridge_device(port_map, port_list, 'br-lan')
            self.assertEqual(conf, exp1_1)

            conf = getconf_vlan_dsa(port_map, port_list, vlan_list, vlan_set, 'br-lan')
            self.assertEqual(conf, exp1_2)

            # with wan
            exp2_1 = """add network device
set network.@device[-1].name='br-lan'
set network.@device[-1].type='bridge'
add_list network.@device[-1].ports=lan1
add_list network.@device[-1].ports=lan2
add_list network.@device[-1].ports=lan3
add_list network.@device[-1].ports=lan4
add_list network.@device[-1].ports=wan
"""

            exp2_2 = """# bridge-vlan

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='1'
add_list network.@bridge-vlan[-1].ports='lan1:u*'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='10'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='20'
add_list network.@bridge-vlan[-1].ports='lan3:u*'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='30'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='80'
add_list network.@bridge-vlan[-1].ports='lan2:u*'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='100'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

"""
            myparam["arg_port_vlan"] = {
                    "WAN":  0,
                    "1":  1,
                    "2": 80,
                    "3": 20,
                    "4":  0,
                }

            port_vlan = myparam['arg_port_vlan']
            [port_list, vlan_list] = port_vlan_to_lists(port_vlan)

            #print(f"port_vlan3={port_vlan}")
            #print(f"port_list3={port_list}")
            #print(f"vlan_list3={vlan_list}")
            conf = _getconf_trunk_bridge_device(port_map, port_list, 'br-lan')
            self.assertEqual(conf, exp2_1)

            conf = getconf_vlan_dsa(port_map, port_list, vlan_list, vlan_set, 'br-lan')
            self.assertEqual(conf, exp2_2)


            # with vlan array

            exp2_1 = """add network device
set network.@device[-1].name='br-lan'
set network.@device[-1].type='bridge'
add_list network.@device[-1].ports=lan1
add_list network.@device[-1].ports=lan2
add_list network.@device[-1].ports=lan3
add_list network.@device[-1].ports=lan4
add_list network.@device[-1].ports=wan
"""

            exp2_2 = """# bridge-vlan

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='1'
add_list network.@bridge-vlan[-1].ports='lan1:u*'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='10'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='20'
add_list network.@bridge-vlan[-1].ports='lan3:u*'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:u*'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='30'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='80'
add_list network.@bridge-vlan[-1].ports='lan2:u*'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

add network bridge-vlan
set network.@bridge-vlan[-1].device='br-lan'
set network.@bridge-vlan[-1].vlan='100'
add_list network.@bridge-vlan[-1].ports='lan4:t'
add_list network.@bridge-vlan[-1].ports='wan:t'

"""
            myparam["arg_port_vlan"] = {
                    "WAN":  [20,0],
                    "1":  1,
                    "2": 80,
                    "3": 20,
                    "4":  0,
                }

            port_vlan = myparam['arg_port_vlan']
            [port_list, vlan_list] = port_vlan_to_lists(port_vlan)

            #print(f"port_vlan3={port_vlan}")
            #print(f"port_list3={port_list}")
            #print(f"vlan_list3={vlan_list}")
            conf = _getconf_trunk_bridge_device(port_map, port_list, 'br-lan')
            self.assertEqual(conf, exp2_1)

            conf = getconf_vlan_dsa(port_map, port_list, vlan_list, vlan_set, 'br-lan')
            self.assertEqual(conf, exp2_2)

        def test_set_merge(self):

            vlan_set = {1,80,20}
            vlan_list = [0, 1,2,80,20]
            vlan_set1 = vlan_set.union({ i for i in vlan_list })
            vlan_set1.discard(0)
            vlan_list_set = list(vlan_set1)
            vlan_list_set.sort()
            self.assertEqual(vlan_list_set, [1,2,20,80])

            port_vlan = {
                    "WAN":  2,
                    "1":  1,
                    "2": 80,
                    "3": 20,
                    "4":  0,
                }
            [port_list, vlan_list] = port_vlan_to_lists(port_vlan)

            self.assertEqual(port_list, ["1","2","3","4","WAN"])
            self.assertEqual(vlan_list, [1,80,20,0,2])

    unittest.main()
