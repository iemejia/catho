from utils import *

import errno
import glob
import logging
import os

catho_path = os.path.join(os.path.expanduser("~"), ".catho")
catho_extension = '.db'

logger = logging.getLogger('catho')

def file_get_catalog_abspath(name):
    return os.path.join(catho_path, name + catho_extension)

def file_get_catalogs():
    catalogs = []
    files = os.listdir(catho_path)
    ext_len = len(catho_extension)
    for filename in files:
        if filename.endswith(catho_extension):
            fullpath = os.path.join(catho_path, filename)
            size, date = get_file_info(fullpath)
            catalogs.append({ 'name' : filename[:-ext_len], 
                              'size' : size,
                              'date' : date })
    return catalogs

def file_select_catalogs(selection = []):
    catalogs = file_get_catalogs()
    if not selection:
        selected = [catalog['name'] for catalog in file_get_catalogs()]
    else:
        selected = [catalog['name'] for catalog in file_get_catalogs() if catalog['name'] in selection]

        if len(selection) != len(selected):
            discarded = [s for s in selection if s not in selected]
            logger.warning('Some catalogs ignored (%s)' % discarded)

    return selected

def path_block_iterator(fullpath, num_files):
    """ returns an iterator of a subcollection of files for the given size: """
    """ path in blocks of size num_files, it contructs a collection  """
    """ of fileitems """
    # links to directories are ignored to avoid recursion fo the instanct
    i = 0
    files = []
    for dirname, dirnames, filenames in os.walk(fullpath):
        # logger.debug(dirname, dirnames, filenames)
        for filename in filenames:
            i += 1
            try:
                rel_path = os.path.relpath(dirname, fullpath)

                # this is the complete file path for each file
                path = os.path.join(dirname, filename)
                size, date = get_file_info(path)
                id = None # since the filesystem doesn't identify ids, added to have simmetry with the db registrs
                hash = None
                # logger.debug((id, filename, date, size, rel_path, hash))
                files.append((id, filename, date, size, rel_path, hash))
                if i == num_files:
                    yield files
                    # we restart the accumulators
                    i = 0
                    files = []
            except OSError as oe:
                if oe.errno == errno.ENOENT:
                    realpath = os.path.realpath(path)
                    logger.error("Ignoring %s. No such target file or directory %s" % (path, realpath))
                else:
                    logger.error("An error occurred processing %s: %s" % (filename,oe))
            except UnicodeDecodeError as ue:
                logger.error("An error occurred processing %s: %s" % (filename, ue))
            except IOError as ioe:
                logger.error("An error occurred processing %s: %s" % (filename, ioe))

    yield files

def calc_hashes(fullpath, files, block_size, hash_type='sha1'):
    """ calc the hash value for each of the elements of the collection if """
    """ it has not been calculated """
    """ returns a list of tuples with the hash calculated """
    hashed_files = []
    for id, name, date, size, path, hash in files:
        if not hash:
            file_path = os.path.join(fullpath, path, name)
            hash = file_hash(file_path, block_size, hash_type)
            logger.debug("Calculating %s for %s | %s" % (hash_type, name, hash))
            hashed_files.append((id, name, date, size, path, hash))
    return hashed_files

def file_rm_catalog_file(catalogs):
    """ deletes the list of cats """
    filelist = [ glob.glob(file_get_catalog_abspath(f)) for f in catalogs ]
    filelist = sum(filelist, [])
    for f in filelist:
        try:
            os.remove(f)
            logger.info("rm %s" % f)
        except OSError:
            logger.error("rm: %s: No such file or directory" % f)
