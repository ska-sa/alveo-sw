import os, mmap, sys, subprocess, zlib
import numpy as np
from time import sleep
#from casperfpga import utils
import fpgparser
import AlveoSensors as sensors


class _AlveoMemMap:
    """
        Class representing Alveo memory map and associated I/O
    """

    def __init__(self, devfile, size):
        """
        Instantiate the object representing the memory map
        :param devfile: typically a device file but regular files could be used for testing
        :param size: size to map
        """
        self.__pcie_bar_size = size
        fd = os.open(devfile, os.O_RDWR | os.O_SYNC)
        self.__mm = mmap.mmap(fd,
                              self.__pcie_bar_size,
                              mmap.MAP_SHARED,
                              mmap.PROT_READ | mmap.PROT_WRITE,
                              offset=0)
        #we don't need to keep the fd around
        os.close(fd)


    def __del__(self):
        self.__mm.close()
        self.__mm = None


    def wordread_aligned(self, offset, size=1) -> tuple:
        """
        Read 32-bit aligned words from the mapped memory region
        :param offset: offset in bytes
        :param size: number of words to read, default=1
        :return: tuple containing bytes of read data
        """
        if (offset % 4) != 0:
            raise MemoryError("offset not aligned to 32-bit word boundary")

        size_in_bytes = size << 2

        if (offset + size_in_bytes) > self.__pcie_bar_size:
            raise MemoryError("attempting buffer over-read")

        #expose mem-region-of-interest as 1-D np array
        buff = np.frombuffer(self.__mm, np.uint32, size, offset)

        #tmp = [hex(x) for x in buff]
        tmp = [x.tobytes() for x in buff]
        return (*tmp,) #return tuple here since this is what katcp lib expects


    def wordwrite_aligned(self, offset, *data_words):
        """
        Write 32-bit data words to word aligned offsets
        :param offset: offset in bytes
        :param data: data to write in byte-like format
        e.g. wordwrite_aligned(0, b'1234', b'\\x01\\x02\\x03\\x04')
        """

        #slightly weird way to check if all elements in the data arg (tuple)
        #are byte-strings - relying on min([...]) to return False if any item
        #in the list is False
        if min([isinstance(el,bytes) for el in data_words]) == False:
            raise ValueError("expecting byte string data")

        if offset < 0:
            raise ValueError("offset must be positive")

        if (offset % 4) != 0:
            raise MemoryError("unaligned access")
        
        #check that each word has 4 bytes
        if max(len(d) for d in data_words) != 4:
            raise ValueError("each byte-element must be of size 4")

        if min(len(d) for d in data_words) != 4:
            raise ValueError("each byte-element must be of size 4")

        #get the number of words requested to be written
        size_in_words = len(data_words)

        size_in_bytes = size_in_words << 2

        if (offset + size_in_bytes) > self.__pcie_bar_size:
            raise MemoryError("attempting buffer over-write")

        #expose mem-mapped-region-of-interest as 1-D array
        buff_array = np.frombuffer(self.__mm, np.uint32, size_in_words, offset)
        
        #create a np array with the data
        data_array = np.frombuffer(b''.join(data_words), np.uint32, size_in_words, 0) 
        
        #assign data to memory region
        buff_array[0:size_in_words] = data_array


    def byteread(self, offset, size=1):
        """
        Read byte(s) in mapped memory from a given offset
        :param offset: offset in bytes to start reading from
        :param size: number of bytes to read
        :return: tuple of bytes read containing byte-strings
        """

        if offset < 0:
            raise ValueError("offset must be positive")

        if (offset + size) > self.__pcie_bar_size:
            raise MemoryError("attempting buffer over-read")

        #expose mem-region-of-interest as 1-D np array of uint8 elements
        buff = np.frombuffer(self.__mm, np.uint8, size, offset)

        tmp = [x.tobytes() for x in buff]
        return (*tmp,) #return tuple here since this is what katcp lib expects


    def bytewrite(self, offset, *data_bytes):
        """
        Write byte(s) to mapped memory at a given byte offset
        :param offset: offset in bytes
        :param data_bytes: bytes to write in b'' format
        """

        if min([isinstance(el,bytes) for el in data_bytes]) == False:
            raise ValueError("expecting byte string data")

        if offset < 0:
            raise ValueError("offset must be positive")

        #check that each byte is one byte long
        if max(len(d) for d in data_bytes) != 1:
            raise ValueError("each byte-element must be of size 1")

        if min(len(d) for d in data_bytes) != 1:
            raise ValueError("each byte-element must be of size 1")

        size_in_bytes = len(data_bytes)

        if (offset + size_in_bytes) > self.__pcie_bar_size:
            raise MemoryError("attempting buffer over-write")

        #expose mem-mapped-region-of-interest as 1-D array
        buff_array = np.frombuffer(self.__mm, np.uint8, size_in_bytes, offset)
        
        #create a np array with the data
        data_array = np.frombuffer(b''.join(data_bytes), np.uint8, size_in_bytes, 0) 
        
        #assign data to memory region
        buff_array[0:size_in_bytes] = data_array



class AlveoUtils:
    """
    Class to wrap Alveo untilities nd I/O
    """

    def __init__(self, alveo_ref, work_dir, pcie_bar_size):
        """
        Instantiate the AlveoUtils object
        :param alveo_ref:       specify the taget alveo in format alveo_N_uXXX
                                where N is the index and XXX is the type e.g. alveo_0_u50
                                run bash cmd 'ls -l /dev/xdma' to get references
        :param work_dir:        working directory for file I/O
        :param pcie_bar_size:   size of the pcie bar set in the xdma axi4lite interface
        """

        #firstly verify referenced alveo
        if not self.__check_valid_alveo(alveo_ref):
            raise RuntimeError("not a valid alveo reference")

        #private variables
        self.__base_path = f'/dev/xdma/'
        self.__devpath = f'{self.__base_path}{alveo_ref}'
        self.__alveo_ref = alveo_ref
        self.__pciaddr = self.__get_pci_addr()
        self.__pcie_bar_size = pcie_bar_size
        self.__mm = _AlveoMemMap(f'{self.__devpath}/user', pcie_bar_size)
        self.__named_reg_map = {}
        self.__DSP_BASE_OFFSET = 0x8000000
        self.__work_dir = work_dir
        self.__assoc_binary = f''


    #private methods
    def __check_valid_alveo(self, alveo_ref):
        """check if the given alveo reference is valid"""
        exists = os.path.exists(f'/dev/xdma/{alveo_ref}')
        return exists


    def __get_pci_addr(self):
        """return alveo pci addr in format <domain>:<bus>:<slot>.<function>"""
        return os.readlink(f'{self.__devpath}/pci')


    def __tear_down(self):
        """
        this method destroys the mmap obj among other things
        usually done before reprogramming the fpga
        """
        del self.__mm


    #less private methods
    def _remove_from_bus(self):
        if os.geteuid() != 0:
            raise EnvironmentError('Root permissions required.')

        with open(f'{self.__devpath}/pci/remove', 'w') as f:
                f.write(str(1))


    def _rescan_bus(self):
        if os.geteuid() != 0:
            raise EnvironmentError('Root permissions required.')

        with open(f'/sys/bus/pci/rescan', 'w') as f:
                f.write(str(1))


    def _reset_pci(self):
        if os.geteuid() != 0:
            raise EnvironmentError('Root permissions required.')
        self._remove_from_bus()
        sleep(2)
        self._rescan_bus()
        sleep(2)
        #TODO at this point, should we re-read all the private variables in case something changed?
        #although it shouldn't since it is "statically" set up in the linux alveo infrastructure


    #public getters
    @property
    def get_dev_path(self):
        """getter for alveo device path reference"""
        return (self.__devpath)


    @property
    def get_pci_addr(self):
        """getter for alveo pci address in format <domain>:<bus>:<slot>.<function>"""
        tmp = self.__pciaddr.strip('/')  #remove trailing & leading '/'
        return (tmp.split('/')[-1])


    @property
    def assoc_binary(self):
        """path of bitfile/binfile associated with this alveo instance"""
        return self.__assoc_binary


    @assoc_binary.setter
    def set_assoc_binary_ext(self, extension):
        """setter for the name of the associated binary - .bit or .bin"""
        
        if extension not in ['bit', 'bin']:
            raise RuntimeError('not a valid extension')

        tmp = self.get_pci_addr
        for char in [':','.']:
            if char in tmp:
                tmp = tmp.replace(char, '-')
        self.__assoc_binary = f'{self.__work_dir}/alveo-{tmp}.{extension}'


    @property
    def get_named_reg_map(self):
        """getter to return the named registers from the fpg in the current context state"""
        return self.__named_reg_map


    @property
    def get_dsp_reg_offset(self):
        """getter to return the offset to dsp reg space on AXI bus (fixed at design time)"""
        return self.__DSP_BASE_OFFSET

    @property
    def get_alveo_sensor_map(self):
        """getter to return the map of the sensors internal to the alveo"""
        return sensors.alveo_sensor_map


    #public methods
    def reset(self) -> None:
        self.__tear_down()
        self._reset_pci()
        
        #remap memmap
        self.__mm = _AlveoMemMap(f'{self.__devpath}/user', self.__pcie_bar_size)
        self.__mm.bytewrite(0x20000,b'\x01')    #start CMS internal ublaze


    def wordread(self, addr, size=1, type_obj='bytes') -> tuple:
        """
        Read words from mapped memory
        :param addr:        base address (32-bit aligned) to read from
        :param size:        number of 32-bit words to read
        :param type_obj:    return type of data - 'bytes', 'int' or 'hex'
        :return:            tuple containing words read in byte-string format
        """
        #TODO some sanity checks on args
        if type_obj not in ['int', 'bytes', 'hex']:
            raise ValueError("type %s not available" % type_obj)

        data_bytes = self.__mm.wordread_aligned(addr, size)

        if type_obj == 'bytes':
            return data_bytes
        elif type_obj == 'int':
            #convert each element to int then return tuple
            return tuple([int.from_bytes(el, byteorder='little') for el in data_bytes])
        elif type_obj == 'hex':
            return tuple([hex(int.from_bytes(el, byteorder='little')) for el in data_bytes])


    def wordwrite(self, addr, *data):
        self.__mm.wordwrite_aligned(addr, *data)
        #TODO read back, compare and return status, or leave this to caller to do?


    def named_wordread(self, reg_name, offset=0, size=1, type_obj='bytes'):
        """
        Read a named register
        :param offset:      offset in word lengths from register base
        :param size:        number of 32-bit words to read
        """

        if offset < 0:
            raise ValueError("offset must be positive")

        if type_obj not in ['int', 'bytes', 'hex']:
            raise ValueError("type %s not available" % type_obj)

        #sanity check to see if symbolic name of register exists
        if not reg_name in self.__named_reg_map:
            raise RuntimeError("not a valid named register")

        #lookup params from reg name map dictionary
        register_offset = self.__named_reg_map[reg_name]['address']
        byte_length = self.__named_reg_map[reg_name]['bytes']

        if ((offset + size) << 2) > byte_length:
            raise BufferError("attempting to read block past the mapped length")

        byte_offset = offset << 2

        return self.wordread(self.__DSP_BASE_OFFSET + register_offset + byte_offset,
                             size=size,
                             type_obj=type_obj)


    def named_wordwrite(self, reg_name, offset, *data):
        """
        :param offset: offset in word lengths from register base
        """
        if offset < 0:
            raise ValueError("offset must be positive")

        #sanity check to see if symbolic name of register exists
        if not reg_name in self.__named_reg_map:
            raise RuntimeError("not a valid named register")

        #TODO check length of data  +++++++++++++++++++++++++++++++++
            
        #lookup from reg name map dictionary
        register_offset = self.__named_reg_map[reg_name]['address']
        byte_length = self.__named_reg_map[reg_name]['bytes']

        if (offset + len(data)) << 2 > byte_length:
            raise BufferError("attempting to write past the mapped length")

        byte_offset = offset << 2

        self.wordwrite(self.__DSP_BASE_OFFSET + register_offset + byte_offset, *data)


    def named_byteread(self, reg_name, offset, size):
        """
        :param offset:  offset in bytes from register base
        :param size:    number of bytes to read
        """
        
        if offset < 0:
            raise ValueError("offset must be positive")

        #sanity check to see if symbolic name of register exists
        if not reg_name in self.__named_reg_map:
            raise RuntimeError("not a valid named register")

        #lookup params from reg name map dictionary
        register_offset = self.__named_reg_map[reg_name]['address']
        byte_length = self.__named_reg_map[reg_name]['bytes']

        if (offset + size) > byte_length:
            raise BufferError("attempting to read past the register boundary")

        return self.__mm.byteread(self.__DSP_BASE_OFFSET + register_offset + offset, size)


    def named_bytewrite(self, reg_name, offset, *data):
        """
        :param offset: in bytes
        """

        if offset < 0:
            raise ValueError("offset must be positive")

        #sanity check to see if symbolic name of register exists
        if not reg_name in self.__named_reg_map:
            raise RuntimeError("not a valid named register")

        #lookup params from reg name map dictionary
        register_offset = self.__named_reg_map[reg_name]['address']
        byte_length = self.__named_reg_map[reg_name]['bytes']

        if (offset + len(data)) > byte_length:
            raise BufferError("attempting to write past the register boundary")

        return self.__mm.bytewrite(self.__DSP_BASE_OFFSET + register_offset + offset, *data)


    def _parse_fpg(self, fpg_filename, inplace=0):
        """
        fpg_filename:   fpg file to parse
        inplace     :   create the bitstream file in same dir as fpg
        """
        #TODO - sanity check - although casperfpga.utils does check
        #but do anyway in case downstream function changes
        #TODO check line 1 for #! kcpfpg to check valid fpg
        meta = fpgparser.parse_fpg(fpg_filename)
        self.__named_reg_map = meta[1]

        __fpgbasename = os.path.splitext(fpg_filename)[0]
        print(__fpgbasename)

        if inplace:
            __bitstream = f'{__fpgbasename}.bitstream'   #this will be renamed just now
        else:
            __bitstream = f'{self.__work_dir}/bitstream.bitstream'

        #decompress gzip'd fpg on the fly - skip over gzip header
        dec = zlib.decompressobj(32 + zlib.MAX_WBITS)

        with open(fpg_filename, 'rb') as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm, open(__bitstream, 'wb') as wr:
            count = 0
            bitstream = 0
            look = 0
            firstline = 1

            for line in iter(mm.readline, b''):
                if firstline == 1:
                    firstline = 0
                    if not line.strip() == b'#!/bin/kcpfpg':
                        raise RuntimeError("not a valid fpg")
                elif bitstream == 0:
                    if line.strip() == b'?quit':
                        bitstream = 1
                    #count = count + 1
                    #print(count, line)
                    continue
                else:
                    data = dec.decompress(line)
                    if data == b'':
                        continue
                    if look == 0:
                        look = 1   #look only in first non-empty chunk
                        # 'aa995566' usually found within first 200 bytes of bitstream (bin/bit)
                        # and should be within the first non zero chunk
                        token_loc = data.find(b'\xaa\x99\x55\x66')
                        if token_loc == -1:
                            raise RuntimeError("is this a valid bitstream?") #TODO
                        else:
                            #distinguish between a bit or bin file.
                            #In a bit file, there's some header
                            #meta data in the first 129 bytes while in the .bin
                            #file there's not, so the apporximate
                            #location of aa996655 token could be used to distinguish
                            #between bit / bin files. Upon inspection, 100 bytes seems
                            #like resonable threshold

                            if token_loc > 100:
                                ext = f'bit'
                            else:
                                ext = f'bin'
                            self.set_assoc_binary_ext = ext

                    wr.write( data )
        #now rename accordingly
        if inplace:
            os.rename(__bitstream, f'{__fpgbasename}{ext}')
        else:
            os.rename(__bitstream, self.assoc_binary)


    def program(self, progfile):
        """
        program with either .bit or .fpg file
        """
        #TODO do sanity check to see if it's a valid prog file
        #for now just check file extension, can do a bit deeper inspection

        #TODO : check the programming call chain and how it should affect the locking
        #mechanisms like statuses and device mapping

        #self.__named_reg_map = {}
        #self.__progstat = 0

        ext = os.path.splitext(progfile)[1]
        if ext == '.fpg':
            self._parse_fpg(progfile, 0)
            self.__program_bitfile(self.assoc_binary)
            #self.__progstat = 1     #TODO this must be guarded by fpg condition
        elif ext == '.bit':
            self.__program_bitfile(progfile)
        
        else:
            raise RuntimeError("not a valid programming file extension")


        #TODO check return code after programming !!


    def __program_bitfile(self, bitfile):
        """
        program a bit file onto the alveo
        """
        #TODO sanity checks

        if os.geteuid() != 0:
            raise EnvironmentError('Root permissions required.')
        bf = os.path.abspath(bitfile)
        #subprocess.call(["ls", "-lha"])
        PROGPATH=f'/opt/alveo/alveo-program/'
        z = subprocess.run([f'{PROGPATH}alveo-program.sh',self.get_pci_addr, bf ], cwd=f'{PROGPATH}')
        #TODO check return code
