#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import hashlib

# this file contains the utils that are global not only to catho, but
# eventually to any other project, so it should not have any
# dependencies apart of python core libraries

def file_touch_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def file_touch_file(name):
    if os.path.exists(name):
        os.utime(name, None)
    else:
        open(name, 'w').close()

def file_rm(name):
    if os.path.exists(name):
        if os.path.isdir(name):
            os.removedirs(path)
        else:
            os.remove(path)

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

def list_of_tuples_to_dict(l):
    d = {}
    for k,v in l:
        d.setdefault(k, v)
    return d
