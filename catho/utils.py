#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

def get_file_info(fullpath):
    """ Return the size and the date for a filename"""
    stat = os.stat(fullpath)
    date = int(stat.st_ctime) # in unix time
    size = stat.st_size # in bytes
    return size, date
