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
import time
import re

import logging
L = logging.getLogger('switch')

################################################################################
# ref: https://www.timeanddate.com/time/zones/
timezone_info={
    # Abbreviation:	[Time zone name,	Location,	Offset]
    'UTC':  ['Coordinated Universal Time',	'Europe',	'+00:00'],
    'GMT':  ['Greenwich Mean Time',	'Europe',	'+00:00'],
    'WET':	['Western European Time',	'Europe',	'+00:00'],
    'CET':	['Central European Time',	'Europe',	'+01:00'],
    'EET':	['Eastern European Time',	'Europe',	'+02:00'],
    'SGT':	['Singapore Time', 'Asia',	'+08:00'],
    'SST':	['Singapore Standard Time',	'Asia',	'+08:00'],
    #'CST':	['China Standard Time',	'Asia',	'+08:00'],
    'HKT':	['Hong Kong Time',	'Asia',	'+08:00'],
    'AWDT':	['Australian Western Daylight Time',	'Australia',	'+09:00'],
    'AWST': ['Australian Western Standard Time',	'Australia',	'+08:00'],
    'ACDT': ['Australian Central Daylight Time',	'Australia',	'+10:30'],
    'ACST':	['Australian Central Standard Time',	'Australia',	'+09:30'],
    'EDT':	['Eastern Daylight Time',	'North America',	'-04:00'],
    'EST':	['Eastern Standard Time',	'North America',	'-05:00'],
    'CDT':	['Central Daylight Time',	'North America',	'-05:00'],
    'CST':	['Central Standard Time',	'North America',	'-06:00'],
    'MDT':	['Mountain Daylight Time',	'North America',	'-06:00'],
    'MST':	['Mountain Standard Time',	'North America',	'-07:00'],
    'PDT':	['Pacific Daylight Time',	'North America',	'-07:00'],
    'PST':	['Pacific Standard Time',	'North America',	'-08:00'],
    'HST':	['Hawaii Standard Time',	'North America',	'-10:00'],
}
def zonestr_to_off(str_zone):
    if str_zone in timezone_info:
        return timezone_info[str_zone][2].replace(':', '')
    return None
def zonestr_to_off2(str_zone):
    if str_zone in timezone_info:
        return timezone_info[str_zone][2]
    return None

# Sun, 31 Jan 2021 09:37:49 -0500
# tm_struct: time.struct_time
def getstr_clock(tm_struct):
    if not tm_struct: return None
    #L.debug("show_info tm = '{0}', tz={1}, gmtoff={2}".format(tm_struct, tm_struct.tm_zone, tm_struct.tm_gmtoff))
    from time import strftime
    str_tm = strftime("%a, %d %b %Y %H:%M:%S", tm_struct)

    if tm_struct.tm_gmtoff:
        hr = tm_struct.tm_gmtoff / (3600)
        mi = tm_struct.tm_gmtoff % (60)
        if hr < 0:
            str_tm += " {0:03.0f}{1:02.0f}".format(hr,mi)
        else:
            str_tm += " +{0:02.0f}{1:02.0f}".format(hr,mi)
    elif tm_struct.tm_zone:
        str_tm += " {0}".format(zonestr_to_off(tm_struct.tm_zone))

    #L.debug("getstr_clock return: '{0}'".format(str_tm))
    return str_tm

# 2021-01-31T09:35:02-05:00
# tm_struct: time.struct_time
def getstr_clock2(tm_struct):
    if not tm_struct: return None
    #L.debug("show_info tm = '{0}', tz={1}, gmtoff={2}".format(tm_struct, tm_struct.tm_zone, tm_struct.tm_gmtoff))
    from time import strftime
    str_tm = strftime("%Y-%m-%dT%H:%M:%S", tm_struct)

    if tm_struct.tm_gmtoff:
        hr = tm_struct.tm_gmtoff / (3600)
        mi = tm_struct.tm_gmtoff % (60)
        if hr < 0:
            str_tm += "{0:03.0f}:{1:02.0f}".format(hr,mi)
        else:
            str_tm += "+{0:02.0f}:{1:02.0f}".format(hr,mi)
    elif tm_struct.tm_zone:
        str_tm += "{0}".format(zonestr_to_off2(tm_struct.tm_zone))

    L.debug("getstr_clock2 return: '{0}'".format(str_tm))
    return str_tm

################################################################################
def parse_clock_openwrt(str_output):
    fmt_search='\s*(.*[0-9]{2}:[0-9]{2}:[0-9]{2}.*)\s*[\r\n]+'
    ln = re.search(fmt_search, str_output).group(0).strip()
    #L.debug("parse_clock ln='{0}'".format(ln))
    exp = None
    try:
        exp = time.strptime(ln, "%a %b %d %H:%M:%S %Z %Y")
    except:
        pass
    if not exp:
        try:
            exp = time.strptime(ln, "%a, %d %b %Y %H:%M:%S %z")
        except:
            pass
    if not exp:
        try:
            exp = time.strptime(ln, "%Y-%m-%dT%H:%M:%S%z")
        except:
            pass

    return exp

def parse_clock_ciscoios(str_output):
    fmt_search='\s*(.*[0-9]{2}:[0-9]{2}:[0-9]{2}.*)\s*[\r\n]+'
    ln = re.search(fmt_search, str_output).group(0).strip()
    ln = ln.replace('*', ' ').strip()
    return time.strptime(ln, "%H:%M:%S.%f %Z %a %b %d %Y")

def parse_clock_arubacli(str_output):
    fmt_search='\s*(.*[0-9]{2}:[0-9]{2}:[0-9]{2}.*)\s*[\r\n]+'
    rs = re.search(fmt_search, str_output)
    if not rs:
        return None
    ln = rs.group(0).strip()
    return time.strptime(ln, "%a %b %d %H:%M:%S %Y")

def parse_clock_dellpc(str_output):
    fmt_search='\s*(.*[0-9]{2}:[0-9]{2}:[0-9]{2}.*)\s*[\r\n]+'
    ln = re.search(fmt_search, str_output).group(0).strip()
    #L.debug("clock ln = {0}".format(ln))
    tmlst = re.split(r'\s+',ln)
    #L.debug("tmlst={0}".format(tmlst))
    str_zone = tmlst[1]
    if re.search(r'\(', str_zone):
        x = str_zone.split("(")
        l1 = x[1]
        y = l1.split(")")
        l2 = y[0]
        str_zone = l2
    zone = int(re.split(r'C',  str_zone)[1].strip())
    #L.debug("zone={0}".format(zone))
    if zone < 0:
        fmt_time = tmlst[0] + " {0:03d}00 ".format(zone) + tmlst[2] + " " + tmlst[3] + " " + tmlst[4]
    else:
        fmt_time = tmlst[0] + " +{0:02d}00 ".format(zone) + tmlst[2] + " " + tmlst[3] + " " + tmlst[4]
    #L.debug("fmt time={0}".format(fmt_time))
    return time.strptime(fmt_time, "%H:%M:%S %z %b %d %Y")


################################################################################
if __name__ == '__main__':
    import mylog
    L = mylog.setup_custom_logger('switch')
    L.setLevel(logging.DEBUG)

    import unittest
    class myTest(unittest.TestCase):

        output_openwrt_clock1 = """root@netlab-1:/etc/config# date
date
Wed Jan 27 03:27:57 EST 2021
root@netlab-1:/etc/config# 
"""
        output_openwrt_clock2 = """root@netlab-1:/etc/config# date -R 
date -R
Wed, 27 Jan 2021 03:26:58 -0500
root@netlab-1:/etc/config# 
"""
        output_openwrt_clock3 = """root@netlab-1:/etc/config# date -Idate -Ihour -Iminute -Isecond
date -Idate -Ihour -Iminute -Isecond
2021-01-27T03:30:45-0500
root@netlab-1:/etc/config# 
"""
        output_openwrt_clock4 = """date -R
Sun, 31 Jan 2021 09:17:44 -0500
"""

        output_ciscoios_clock1="""Switch#show clock
*13:13:15.087 EST Fri Mar 1 2002
Switch#
"""
        output_ciscoios_clock2="""Switch#show clock detail
*13:10:15.787 EST Fri Mar 1 2002
No time source
Summer time starts 02:00:00 EST Sun Mar 10 2002
Summer time ends 02:00:00 EDT Sun Nov 3 2002
Switch#
"""
        output_ciscoios_clock3="""Switch#show clock
09:12:37.655 EST Sat Jan 30 2021
Switch#
"""
        output_ciscoios_clock4="""Switch#show clock detail
09:12:43.563 EST Sat Jan 30 2021
Time source is user configuration
Summer time starts 02:00:00 EST Sun Mar 14 2021
Summer time ends 02:00:00 EDT Sun Nov 7 2021
Switch#
"""

        output_arubacli_clock1 = """HP-2920-24G-PoEP# show time
Mon Jan  1 02:39:50 1990
HP-2920-24G-PoEP# 
"""

        output_dellpc_clock0='''Switch(config)# clock timezone +8 zone CST
clock timezone +8 zone CST
Switch# show clock
show clock
 10:04:33 CST(UTC+8)  Jan 1 2000
Time source is sntp
'''
        output_dellpc_clock1='''Switch# show clock
show clock
 20:05:40 (UTC-5)  Dec 31 2099
Time source is sntp
'''
        output_dellpc_clock2='''Switch# show clock
show clock
 20:05:40 (UTC-3)  Dec 31 2099
Time source is sntp
'''
        output_dellpc_clock3='''Switch(config)# clock timezone +8 zone UTC
clock timezone +8 zone UTC
Switch(config)# 
Switch(config)# exit
exit
Switch# 
Switch# show clock
show clock
 10:05:25 UTC+8 Jan 1 2000
Time source is sntp
'''
        def test_clock_openwrt(self):
            fmt = "%a %b %d %H:%M:%S %Z %Y"
            exp = time.strptime( "Wed Jan 27 03:27:57 EST 2021", fmt)
            self.assertEqual(exp, parse_clock_openwrt(self.output_openwrt_clock1))
            fmt = "%a, %d %b %Y %H:%M:%S %z"
            exp = time.strptime( "Wed, 27 Jan 2021 03:26:58 -0500", fmt)
            self.assertEqual(exp, parse_clock_openwrt(self.output_openwrt_clock2))
            fmt = "%Y-%m-%dT%H:%M:%S%z"
            exp = time.strptime( "2021-01-27T03:30:45-0500", fmt)
            self.assertEqual(exp, parse_clock_openwrt(self.output_openwrt_clock3))
            fmt = "%a, %d %b %Y %H:%M:%S %z"
            exp = time.strptime( "Sun, 31 Jan 2021 09:17:44 -0500", fmt)
            self.assertEqual(exp, parse_clock_openwrt(self.output_openwrt_clock4))

        def test_clock_ciscoios(self):
            #exp = time.struct_time(tm_year=2099, tm_mon=12, tm_mday=31, tm_hour=20, tm_min=5, tm_sec=40)
            exp = time.strptime( "20:05:40 (UTC-5)  Dec 31 2099", "%H:%M:%S (UTC-5) %b %d %Y")
            fmt_search='\s*(.*[0-9]{2}:[0-9]{2}:[0-9]{2}.*)\s*[\r\n]+'
            str_line = re.search(fmt_search, self.output_ciscoios_clock1).group(0).strip()
            L.info("split={0}".format(str_line.split('[\(\)]', 2)))
            L.info("expect time={0}".format(exp))
            L.info("time match='{0}'".format( re.search(fmt_search, self.output_ciscoios_clock1).group(0).strip() ))
            self.assertEqual(re.search(fmt_search, self.output_ciscoios_clock1).group(0).strip(), '*13:13:15.087 EST Fri Mar 1 2002')

            fmt = "%H:%M:%S.%f %Z %a %b %d %Y"
            exp = time.strptime( "13:13:15.087 EST Fri Mar 1 2002", fmt)
            L.info("exp={0}".format(exp))
            self.assertEqual(exp, parse_clock_ciscoios(self.output_ciscoios_clock1))
            exp = time.strptime( "13:10:15.787 EST Fri Mar 1 2002", fmt)
            self.assertEqual(exp, parse_clock_ciscoios(self.output_ciscoios_clock2))
            exp = time.strptime( "09:12:37.655 EST Sat Jan 30 2021", fmt)
            self.assertEqual(exp, parse_clock_ciscoios(self.output_ciscoios_clock3))
            exp = time.strptime( "09:12:43.563 EST Sat Jan 30 2021", fmt)
            self.assertEqual(exp, parse_clock_ciscoios(self.output_ciscoios_clock4))

        def test_clock_arubacli(self):
            #exp = time.struct_time(tm_year=2099, tm_mon=12, tm_mday=31, tm_hour=20, tm_min=5, tm_sec=40)
            exp = time.strptime( "20:05:40 (UTC-5)  Dec 31 2099", "%H:%M:%S (UTC-5) %b %d %Y")
            fmt_search='\s*(.*[0-9]{2}:[0-9]{2}:[0-9]{2}.*)\s*[\r\n]+'
            str_line = re.search(fmt_search, self.output_arubacli_clock1).group(0).strip()
            L.info("split={0}".format(str_line.split('[\(\)]', 2)))
            L.info("expect time={0}".format(exp))
            L.info("time match='{0}'".format( re.search(fmt_search, self.output_arubacli_clock1).group(0).strip() ))
            self.assertEqual(re.search(fmt_search, self.output_arubacli_clock1).group(0).strip(), 'Mon Jan  1 02:39:50 1990')

            fmt = "%a %b %d %H:%M:%S %Y"
            exp = time.strptime( "Mon Jan  1 02:39:50 1990", fmt)
            L.info("exp={0}".format(exp))
            self.assertEqual(exp, parse_clock_arubacli(self.output_arubacli_clock1))

        def test_clock_dellpc(self):
            #exp = time.struct_time(tm_year=2099, tm_mon=12, tm_mday=31, tm_hour=20, tm_min=5, tm_sec=40)
            exp = time.strptime( "20:05:40 (UTC-5)  Dec 31 2099", "%H:%M:%S (UTC-5) %b %d %Y")
            fmt_search='\s*(.*[0-9]{2}:[0-9]{2}:[0-9]{2}.*)\s*[\r\n]+'
            str_line = re.search(fmt_search, self.output_dellpc_clock1).group(0).strip()
            L.info("split={0}".format(str_line.split('[\(\)]', 2)))
            L.info("expect time={0}".format(exp))
            L.info("time match='{0}'".format( re.search(fmt_search, self.output_dellpc_clock1).group(0).strip() ))
            self.assertEqual(re.search(fmt_search, self.output_dellpc_clock1).group(0).strip(), '20:05:40 (UTC-5)  Dec 31 2099')

            fmt = "%H:%M:%S %z %b %d %Y"
            exp = time.strptime( "20:05:40 -0500 Dec 31 2099", fmt)
            self.assertEqual(exp, parse_clock_dellpc(self.output_dellpc_clock1))
            exp = time.strptime( "20:05:40 -0500 Dec 31 2099", fmt)
            self.assertEqual(exp, parse_clock_dellpc(self.output_dellpc_clock2))
            exp = time.strptime( "10:05:25 +0800 Jan 1 2000", fmt)
            self.assertEqual(exp, parse_clock_dellpc(self.output_dellpc_clock3))

        def test_getstr_clock(self):

            timest = time.strptime("Wed Jan 27 03:27:57 EST 2021", "%a %b %d %H:%M:%S %Z %Y")
            exp_1 = "Wed, 27 Jan 2021 03:27:57 -0500"
            exp_2 = "2021-01-27T03:27:57-05:00"
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))
            timest = parse_clock_openwrt(self.output_openwrt_clock1)
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))

            timest = time.strptime("13:13:15.087 EST Fri Mar 1 2002", "%H:%M:%S.%f %Z %a %b %d %Y")
            exp_1 = "Fri, 01 Mar 2002 13:13:15 -0500"
            exp_2 = "2002-03-01T13:13:15-05:00"
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))
            timest = parse_clock_ciscoios(self.output_ciscoios_clock1)
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))

            timest = time.strptime("Mon Jan  1 02:39:50 1990", "%a %b %d %H:%M:%S %Y")
            exp_1 = "Mon, 01 Jan 1990 02:39:50"
            exp_2 = "1990-01-01T02:39:50"
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))
            timest = parse_clock_arubacli(self.output_arubacli_clock1)
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))

            timest = time.strptime("20:05:40 -0500 Dec 31 2099", "%H:%M:%S %z %b %d %Y")
            exp_1 = "Thu, 31 Dec 2099 20:05:40 -0500"
            exp_2 = "2099-12-31T20:05:40-05:00"
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))
            timest = parse_clock_dellpc(self.output_dellpc_clock1)
            self.assertEqual(exp_1, getstr_clock(timest))
            self.assertEqual(exp_2, getstr_clock2(timest))

    unittest.main()
