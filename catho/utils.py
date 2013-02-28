#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

def get_file_info(basepath, filename):
    """ Return the size and the date for a filename"""
    fullpath = os.path.join(basepath, filename)

    stat = os.stat(fullpath)
    date = int(stat.st_ctime)
    size = stat.st_size # in bytes
    return size, date
