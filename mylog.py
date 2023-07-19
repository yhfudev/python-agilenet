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

import logging

FMT_LOGGING='%(asctime)s|%(levelname)-1s|%(module)s - %(message)s'

def setup_custom_logger(name):
    # fmt='%(asctime)s %(levelname)-5s %(name)-5s %(message)s'
    formatter = logging.Formatter(fmt=FMT_LOGGING)

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    #logger.setLevel(logging.DEBUG)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

def add_file_logger(name, file_name, level=logging.INFO):
    L = logging.getLogger(name)
    L.info ("output log to " + file_name)
    ch = logging.FileHandler(file_name)
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(FMT_LOGGING))
    logging.getLogger().addHandler(ch)
