#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

def get_file_info(fullpath):
    """ Return the size and the date for a filename"""
    stat = os.stat(fullpath)
    date = int(stat.st_ctime) # in unix time
    size = stat.st_size # in bytes
    return size, date

def sizeof_fmt(num):
    for x in ['bytes','KB','MB','GB','TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
