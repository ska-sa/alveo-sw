#NOTE this was copy-pasted from casperfpga
#to eliminate the need to install it

import logging

LOGGER = logging.getLogger(__name__)

def parse_fpg(filename, isbuf=False):
    """
    Read the meta information from the FPG file.

    :param filename: the name of the fpg file to parse
    :param isbuf: If True, the filename is not actually a name, it is a
        BytesIO buffer.
    :return: device info dictionary, memory map info (coreinfo.tab) dictionary
    """


    LOGGER.debug('Parsing file %s for system information' % filename)
    if filename is not None:
        if not isbuf:
            fptr = open(filename, 'rb')
        else:
            fptr = filename
        firstline = fptr.readline().decode('latin-1').strip().rstrip('\n')
        if firstline != '#!/bin/kcpfpg':
            fptr.close()
            raise RuntimeError('%s does not look like an fpg file we can '
                               'parse.' % filename)
    else:
        raise IOError('No such file %s' % filename)

    memorydict = {}
    metalist = []
    while True:
        line = fptr.readline().decode('latin-1').strip().rstrip('\n')
        if line.lstrip().rstrip() == '?quit':
            break
        elif line.startswith('?meta'):
            # some versions of mlib_devel may mistakenly have put spaces
            # as delimiters where tabs should have been used. Rectify that
            # here.
            if line.startswith('?meta '):
                LOGGER.warn('An old version of mlib_devel generated %s. Please '
                            'update. Meta fields are seperated by spaces, '
                            'should be tabs.' % filename)
                line = line.replace(' ', '\t')
            # and carry on as usual.
            line = line.replace('\_', ' ').replace('?meta', '')
            line = line.replace('\n', '').lstrip().rstrip()
            #line_split = line.split('\t')
            # Rather split on any space
            line_split = line.split()
            name = line_split[0]
            tag = line_split[1]
            param = line_split[2]
            if len(line_split[3:]) == 1:
                value = line_split[3:][0]
            else:
                value = ' '.join(line_split[3:])
            # name, tag, param, value = line.split('\t')
            name = name.replace('/', '_')
            metalist.append((name, tag, param, value))
        elif line.startswith('?register'):
            if line.startswith('?register '):
                register = line.replace('\_', ' ').replace('?register ', '')
                register = register.replace('\n', '').lstrip().rstrip()
                name, address, size_bytes = register.split(' ')
            elif line.startswith('?register\t'):
                register = line.replace('\_', ' ').replace('?register\t', '')
                register = register.replace('\n', '').lstrip().rstrip()
                name, address, size_bytes = register.split('\t')
            else:
                raise ValueError('Cannot find ?register entries in '
                                 'correct format.')
            address = int(address, 16)
            size_bytes = int(size_bytes, 16)
            if name in memorydict.keys():
                raise RuntimeError('%s: mem device %s already in '
                                   'dictionary' % (filename, name))
            memorydict[name] = {'address': address, 'bytes': size_bytes}
    fptr.close()
    return create_meta_dictionary(metalist), memorydict




def create_meta_dictionary(metalist):
    """
    Build a meta information dictionary from a provided raw meta info list.

    :param metalist: a list of all meta information about the system
    :return: a dictionary of device info, keyed by unique device name
    """
    meta_items = {}
    try:
        for name, tag, param, value in metalist:
            if name not in meta_items:
                meta_items[name] = {}
            try:
                if meta_items[name]['tag'] != tag:
                    raise ValueError(
                        'Different tags - %s, %s - for the same item %s' % (
                            meta_items[name]['tag'], tag, name))
            except KeyError:
                meta_items[name]['tag'] = tag
            meta_items[name][param] = value
    except ValueError as e:
        for ctr, contents in enumerate(metalist):
            print(ctr, end='')
            print(contents)
        raise e
    return meta_items
