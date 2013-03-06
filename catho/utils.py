#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import hashlib

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

def file_hash(filename, block_size, hash_type = 'sha1'):
    """ calculates the hash for the file in filename """
    """ default implementation calcs sha1 """
    """ the hash is calculated in blocs of size block_size, so larger
    files can be supported """
    # todo should we use the git convention for this ?
    # sha1("blob " + filesize + "\0" + data)

    # if hash_type != 'sha1':
    #     h = hashlib.new(hash_type) # more generic call
    h = hashlib.sha1()
    f = open(filename, 'rb')
    try:
        while True:
            data = f.read(block_size)
            if not data:
                break
            h.update(data)
    finally:
        f.close()
    hash = h.hexdigest()
    return hash

def list_of_tuples_to_dir(l):
    d = {}
    for k,v in l:
        d.setdefault(k, v)
    return d
