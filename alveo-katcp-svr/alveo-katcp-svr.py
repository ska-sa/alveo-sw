#!/usr/bin/env python3

import aiokatcp
import asyncio
import socket
import os
import argparse
import logging
import numpy as np
import sys

from AlveoIO import AlveoUtils

#NOTES:
#   all filesystem operation only allowed on the given working directory

PCIE_BAR_SIZE = 1 << 28

class MyServer(aiokatcp.DeviceServer):
    
    VERSION = 'myserver-api-1.0'
    BUILD_STATE = 'myserver-1.0.1.dev0'
    #wd = os.path.abspath('.')
    #alveo = AlveoPcieUtils('alveo_0_u50', wd)

    def __init__(self, ip, port, alveo_ref, wd, card, *args, **kwargs):
        super().__init__(ip, port, *args, **kwargs)
        self.wd = wd #os.path.abspath('.')
        #self.alveo = AlveoPcieUtils('alveo_0_u50', self.wd)
        self.alveo = AlveoUtils(alveo_ref, self.wd, PCIE_BAR_SIZE)
        sensor = aiokatcp.Sensor(
            str,
            "alveo-sn",
            "alveo serial number",
            default=card,
            initial_status=aiokatcp.Sensor.Status.NOMINAL,
        )
        self.sensors.add(sensor)
        self.VERSION = card

#        sensor = aiokatcp.Sensor(
#            float,
#            "uptime",
#            "uptime of server since boot",
#            default=0,
#            initial_status=aiokatcp.Sensor.Status.NOMINAL,
#        )
#        self.sensors.add(sensor)
#        self.add_service_task(asyncio.create_task(self._alter_sensors()))
#        #TODO check if there's not a callback that gets run when sensor-value
#        # is called to hook into
#
#    async def _service_task(self) -> None:
#        """Example service task that broadcasts to clients."""
#        while True:
#            #TODO this feels like a lot of filesystem IO too often (?)
#            await asyncio.sleep(1)
#            with open('/proc/uptime', 'r') as f:
#                uptime_seconds = float(f.readline().split()[0])
#            #self.mass_inform("uptime", uptime_seconds)
#            self.sensors["uptime"].value = uptime_seconds

 
    async def request_greet(self, ctx, name: str) -> None:
        """Take a person's name and greet them"""
        ctx.inform(name)
        #return 'hello', name
        raise aiokatcp.FailReply(f"{name} error")
        #return

#TODO turn the params like dev path and pci addr into sensors rather
    async def request_alveo_dev(self, ctx):
        """get alveo dev reference"""
        return self.alveo.get_dev_path

    async def request_alveo_pci(self, ctx):
        """get alveo pci addr"""
        return self.alveo.get_pci_addr

    async def request_alveo_reset(self, ctx):
        """reset alveo"""
        return self.alveo.reset()



    
    async def request_alveo_memread(self, ctx, addr: str, words='1'):
        """read addr from memory (?alveo-memread addr [words])"""
        #TODO perhaps only allow hex values - throw error here if not
        addr_int = int(addr, 0)

        #NOTE it's possible to read multiple words but for now, keeping it
        #to one word reads
        #words_int = int(words, 0)
        words_int = 1
        #return self.alveo.mem_read(addr_int, words_int)
        ctx.inform(addr, *self.alveo.wordread(addr_int, words_int, 'hex'))
        return


    
    async def request_alveo_memwrite(self, ctx, addr: str, data: str) -> None:
        """read addr from memory"""
        
        #TODO perhaps only allow hex values - throw error here if not
        print(data)

        addr_int = int(addr, 0)     #set arg to string and then
                                    #convert in order to allow for 0x.. prefix
        data_int = int(data, 0)
        
        try:
            data = int(data, 0).to_bytes(4, 'little')
        except OverflowError as err:
            raise aiokatcp.FailReply(f'{err} - 32-bit data words required')
        except ValueError:
            raise aiokatcp.FailReply("only numeric data allowed")

        #TODO - multiple word writes

        #return self.alveo.mem_write(addr_int, data_int)
        self.alveo.wordwrite(addr_int, data)

        #TODO redback!!!!
#        #read back and verify
        (readback_data,) = self.alveo.wordread(addr_int, 1, 'hex')
#        #print(readback_data)
#        #print(type(readback_data))
        if readback_data == hex(data_int):
            ctx.inform(addr, readback_data)
        else:
            raise aiokatcp.FailReply(f'write-error @ {addr}')


    async def request_alveo_program(self, ctx, bitfile='default'):
        """program bitfile"""
        if bitfile == 'default':
            bf = self.alveo.assoc_binary
        else:
            bf = bitfile.decode()     #bytes to string
        
        bf = os.path.abspath(bf)

        if not os.path.exists(bf):
            raise aiokatcp.connection.FailReply("bit file note found")
        else:
            self.alveo.program(bf)
        #print(self.wd)
        return

    async def request_listbof(self, ctx):
        """list files"""
        ls = os.listdir(self.wd)
        #print(ls)
        for d in ls:
            ctx.inform(d)
        return


    async def request_listdev(self, ctx):
        """ lists available registers"""
        #self.alveo._parse_fpg('casper_pfb_au50_1k_8in_1pol_2022-11-11_1146.fpg')
        devs = self.alveo.get_named_reg_map
        if not devs:
            ctx.inform('fpg not mapped')
            raise aiokatcp.FailReply('unampped')
        else:
            keys = [name for name in devs.keys()]
            #print(keys)
            for d in keys:
                ctx.inform(d)
        #ctx.inform(*tuple(d for d in devs.keys()))
        return


    async def request_wordread(self, ctx,
            named_reg: str,
            offsets=str(0),
            size=str(1)):
        """read a number of words from the given byte offset (wordread register_name offset_in_words size_in_words)"""

        #offsets should be in the format word_offset:bit_offset
        #OR simply just word_offset - this is to maintain backw
        #compatibility with tcpbs
        #print(type(offsets))
        #print(type(size))

        if type(offsets) == bytes:
            offsets = offsets.decode()

        if type(size) == bytes:
            size = size.decode()

        if not offsets.count(':') in [0 , 1]:
            raise aiokatcp.FailReply('offset syntax error')

        try:
            word_offset_int = int(offsets.split(':')[0], 0)
        except ValueError:
            raise aiokatcp.FailReply('offset syntax error')
        
        try: #user may not have supplied ':bit_offset'
            bit_offset_int = int(offsets.split(':')[1], 0)
        except IndexError:
            #TODO bit_offset seems unused in tcpbs impl anyway?
            pass

        try:
            size_int = int(size, 0)
        except ValueError:
            raise aiokatcp.FailReply('length syntax error')

        if size_int < 1:
            raise aiokatcp.FailReply('read length less than one')

        #do some addressing calculations


        devs = self.alveo.get_named_reg_map
        if not devs:
            ctx.inform('fpg not mapped')
            raise aiokatcp.FailReply('unmapped')
       
        if named_reg in devs:
            try:
                data = self.alveo.named_wordread(named_reg, word_offset_int, size_int, 'hex')
            except BufferError:
                raise aiokatcp.FailReply('attempting to read past register boundary')
            except ValueError as err:
                raise aiokatcp.FailReply(err)
            #except:
                #TODO: return better error info to user - raise custom exceptions from alveo obj
                #and catch them here
            #    raise aiokatcp.FailReply('read error')
        else:
            raise aiokatcp.FailReply(f'{named_reg} not found')

        return data


    async def request_wordwrite(self, ctx, named_reg: str, index: str, *data: str) -> None:
        """wordwrite"""
        """write a number of wordsto the given byte offset (wordwrite register_name offset_in_words data)"""

        try:
            data = tuple([int(d, 0).to_bytes(4, 'little') for d in data])
        except OverflowError as err:
            raise aiokatcp.FailReply(f'{err} - 32-bit data words required')
        except ValueError:
            raise aiokatcp.FailReply("only numeric data allowed")

        index = int(index, 0)

#        data_int = int(data, 0)     #set arg to string and then
#                                    #convert in order to allow for 0x.. prefix
#
#        index_int = int(index, 0)   #TODO for backwrd compatibility with tcpbs
#
#        #TODO: do we want to guard this if fpg parsed ie we have device list but
#        #fpga not programmed - since these are two decoupled commands. Should
#        #really think about combining this functionality (progdev and program) -
#        #this is a legacy artefact
#
        devs = self.alveo.get_named_reg_map
        if not devs:
            ctx.inform('fpg not mapped')
            raise aiokatcp.FailReply('unmapped')
 
        if named_reg in devs:
            try:
                self.alveo.named_wordwrite(named_reg, index, *data)
            except BufferError:
                raise aiokatcp.FailReply('attempting to write past register boundary')
            except ValueError as err:
                raise aiokatcp.FailReply(err)
            except:
                raise aiokatcp.FailReply('write error')
        else:
            raise aiokatcp.FailReply(f'{named_reg} not found')
        
#
#        #read back and verify
#        (readback_data,) = self.alveo.named_read(named_reg, 1, index_int)
#        #print(readback_data)
#        #print(type(readback_data))
#        if readback_data == hex(data_int):
#            ctx.inform(named_reg, readback_data)
#        else:
#            raise aiokatcp.FailReply(f'write-error @ {named_reg}')
#

    async def request_progdev(self, ctx, filename: str) -> None:
        """progdev"""
        self.alveo._parse_fpg(filename)

    async def request_status(self, ctx):
        """fpga status"""
        #TODO actually check status and state
        #dummy function for now to satify casperfpga program cmd flow
        return

    async def request_delbof(self, ctx, filename):
        """fpga status"""
        #TODO actually do the work
        #dummy function for now to satify casperfpga program cmd flow
        logging.getLogger().info("testing the logging")
        return


######################################################################

    async def request_write(self, ctx, named_reg: str, offset: str, data: bytes) -> None:
        """write"""
        #print(type(data))
        #print('data', data)
        #print('offset', offset)

        data_bytes = tuple([el.to_bytes(1,'little') for el in data])

        #TODO have to sort out the write sizes and offsets in all read and write functions

        #data_int = int.from_bytes(data, byteorder='little')
        offset_int = int(offset, 0)  #TODO for backwrd compatibility with tcpbs
        #print('wr offset ', offset_int)

        devs = self.alveo.get_named_reg_map
        if not devs:
            ctx.inform('fpg not mapped')
            raise aiokatcp.FailReply('unmapped')
       
        try:
            self.alveo.named_bytewrite(named_reg, offset_int, *data_bytes)
        except Exception as err:
            raise aiokatcp.FailReply(err)


    async def request_read(self, ctx,
            named_reg: str,
            offset=str(0),          #offset in bytes
            read_len_bytes=str(4)): #length in bytes
        """read"""
        len_int = int(read_len_bytes, 0)
        offset_int = int(offset, 0)

        devs = self.alveo.get_named_reg_map
        if not devs:
            ctx.inform('fpg not mapped')
            raise aiokatcp.FailReply('unmapped')

        try:
            data = self.alveo.named_byteread(named_reg, offset_int, len_int)
            #above function returns a tuple of one-byte elements
            #need to concatenate into one long byte-string
            bytestring = b''.join(data)

        except Exception as err:
            raise aiokatcp.FailReply(err)
        else:
            return bytestring

#
#        #NOTES: historiclly, this function allowed bit- and byte-grained
#        #access to register reads. In  bid to get it working on the alveo,
#        #will only do word accesses for now - ie. round up to the nearest
#        #word boundary in byte length
#        read_len_bytes = int(4 * np.ceil(len_int/4))
#        print(read_len_bytes)
#        read_len_words = (read_len_bytes) >> 2
#        print(read_len_words)
#
        # FIXME actually receiving a byte offset
#        word_offset_int = int(offset, 0) >> 2
#
#        data_string = self.alveo.named_wordread(named_reg, read_len_words, word_offset_int)
#        data_string = self.alveo.named_read(named_reg, read_len_words, 0)
#        data_string = (b'\xde\xad\xbe\xef',)
#        
##        print(data_string)
##        for word in data_string:
##            print(word)
##            for b in range(0,4):
##                byte = (int(word,0) >> (b*8)) & 0xff
##                print(f'0x{byte:x}')
#
#        #f'{int(b[i],0) : x}')
#        data_string_fmtd = f'{int(data_string[0],0):x}'
#        print(data_string_fmtd)

        #return b'\x31\x32\x33\x00'
        #return bytes.fromhex(data_string_fmtd)
#        byte_str = b''
#        for word in data_string:
#            for b in range(0,4):
#                byte = (int(word,0) >> (b*8)) & 0xff
#                byte_str = b''.join([byte_str,byte.to_bytes(1,'big')])

        #print(byte_str)
        #print(type(byte_str))
 #       return byte_str

#######################################################################
    async def request_saveremote(self, ctx, port: str, filename: str):
        """Upload a file to the remote filesystem"""
        SVR = "0.0.0.0"
        #PORT = 10000
        PORT = int(port)

        CHUNK = 4096

        socket.setdefaulttimeout(10)
        #socket.settimeout(10)
        sock = socket.socket()
        sock.bind((SVR, PORT))
        sock.listen(1)
        
        print(f"[*] Listening as {SVR}:{PORT}")

        try:
            client_socket, address = sock.accept()
        except socket.timeout:
            raise aiokatcp.FailReply(f'timeout')


        print(f"[+] {address} is connected.")

        count=0

        with open(filename, "wb") as f:
          while True:
            bytes_read = client_socket.recv(CHUNK)
            if not bytes_read:
              # nothing is received
              # file transmitting is done
              break
            # write to the file the bytes we just received
            if count % 100 == 0:
                print(count)
            count=count+1
            f.write(bytes_read)
        
        f.close()
        # close the client socket
        client_socket.close()
        # close the server socket
        sock.close()
        return

#######################################################################
async def main(foo):

    #alveo = args.alveo
    #workdir=args.workdir

    server = MyServer('0.0.0.0', foo.port, foo.alveo, foo.workdir, foo.card)

    logging.basicConfig(level=logging.INFO)
    handler = MyServer.LogHandler(server)
    logging.getLogger().addHandler(handler)
    
    await server.start()
    await server.join()

def daemonise():
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)
    except OSError as e:
        sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
        sys.exit(1)
       
    # decouple from parent environment
    os.chdir("/")
    os.setsid()
    os.umask(0)
       
    # do second fork
    try:
         pid = os.fork()
         if pid > 0:
            # exit from second parent
            sys.exit(0)
    except OSError as e:
         sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
         sys.exit(1)
       
#                # redirect standard file descriptors
#                sys.stdout.flush()
#                sys.stderr.flush()
#                si = file(self.stdin, 'r')
#                so = file(self.stdout, 'a+')
#                se = file(self.stderr, 'a+', 0)
#                os.dup2(si.fileno(), sys.stdin.fileno())
#                os.dup2(so.fileno(), sys.stdout.fileno())
#                os.dup2(se.fileno(), sys.stderr.fileno())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--alveo',    required=True, metavar='<alveo_ref>', type=str)
    parser.add_argument('-w', '--workdir',  required=True, metavar='<working_dir>', type=str)
    parser.add_argument('-p', '--port',  required=True, metavar='<port>', type=str)
    parser.add_argument('-c', '--card',  required=True, metavar='<card>', type=str)
    parser.add_argument('-d', '--daemon',  action='store_true')
    
    args = parser.parse_args()
 
    if args.daemon == True:
        daemonise()   
        #at this point we should be in the daemon process???

    asyncio.get_event_loop().run_until_complete(main(args))
    asyncio.get_event_loop().close()
