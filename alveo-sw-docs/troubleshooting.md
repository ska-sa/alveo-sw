# Troubleshooting the alveo-sw infrastructure

Listed below are some basic sanity checks to verify that various parts of the Alveo software infrastructure is running correctly.

---
Currently, the Alveo cards are configured using *jtag* programmers. In order for the Alveo software infrastructure to configure the correct card, a mapping between a specific Alveo's *pcie* bus and the *jtag* programmer is configured during installation. To check this mapping, the following command can be executed

```
$ cat /opt/alveo/alveo-program/alveo-pci-cfg
0000:c2:00.0 500202A3099A 3150
0000:c1:00.0 500202A30D7A 3160
```
The columns shown are the *pcie* address, the *jtag* serial number and the port number used by the hardware server during programming.

---
To ensure that 1) the Alveo has been correctly flashed 2) that it is correctly detected and enumerated on the pcie bus and 3) that the XDMA driver has loaded correctly, the following command can be issued from the linux cmd line
```
lspci -d 10ee: -vvv -D
```
This should list ALL Xilinx cards on the pcie bus. It would include Alveos FLASHED with the SARAO BSP, as well as Alveos running the default (factory) shell image. The output should look as follows (or similar):
```
81:00.0 Processing accelerators: Xilinx Corporation Device 500c
	Subsystem: Xilinx Corporation Device 000e
	Control: I/O- Mem- BusMaster- SpecCycle- MemWINV- VGASnoop- ParErr- Stepping- SERR- FastB2B- DisINTx-
	Status: Cap+ 66MHz- UDF- FastB2B- ParErr- DEVSEL=fast >TAbort- <TAbort- <MAbort- >SERR- <PERR- INTx-
	NUMA node: 0
	Region 0: Memory at 47df2000000 (64-bit, prefetchable) [disabled] [size=32M]
	Region 2: Memory at 47df4000000 (64-bit, prefetchable) [disabled] [size=128K]
	Capabilities: <access denied>
	Kernel modules: xclmgmt

81:00.1 Processing accelerators: Xilinx Corporation Device 500d
	Subsystem: Xilinx Corporation Device 000e
	Control: I/O- Mem+ BusMaster+ SpecCycle- MemWINV- VGASnoop- ParErr- Stepping- SERR- FastB2B- DisINTx-
	Status: Cap+ 66MHz- UDF- FastB2B- ParErr- DEVSEL=fast >TAbort- <TAbort- <MAbort- >SERR- <PERR- INTx-
	Latency: 0, Cache Line Size: 64 bytes
	Interrupt: pin A routed to IRQ 128
	NUMA node: 0
	Region 0: Memory at 47df0000000 (64-bit, prefetchable) [size=32M]
	Region 2: Memory at 47df4020000 (64-bit, prefetchable) [size=64K]
	Region 4: Memory at 47de0000000 (64-bit, prefetchable) [size=256M]
	Capabilities: <access denied>
	Kernel driver in use: xocl
	Kernel modules: xocl

c1:00.0 Serial controller: Xilinx Corporation Device 9031 (prog-if 01 [16450])
	Subsystem: Xilinx Corporation Device 0007
	Control: I/O- Mem+ BusMaster+ SpecCycle- MemWINV- VGASnoop- ParErr- Stepping- SERR- FastB2B- DisINTx-
	Status: Cap+ 66MHz- UDF- FastB2B- ParErr- DEVSEL=fast >TAbort- <TAbort- <MAbort- >SERR- <PERR- INTx-
	Latency: 0, Cache Line Size: 64 bytes
	Interrupt: pin A routed to IRQ 125
	NUMA node: 0
	Region 0: Memory at c0000000 (32-bit, non-prefetchable) [size=256M]
	Region 1: Memory at d0000000 (32-bit, non-prefetchable) [size=64K]
	Capabilities: <access denied>
	Kernel driver in use: xdma
	Kernel modules: xdma

c2:00.0 Serial controller: Xilinx Corporation Device 9031 (prog-if 01 [16450])
	Subsystem: Xilinx Corporation Device 0007
	Control: I/O- Mem+ BusMaster+ SpecCycle- MemWINV- VGASnoop- ParErr- Stepping- SERR- FastB2B- DisINTx-
	Status: Cap+ 66MHz- UDF- FastB2B- ParErr- DEVSEL=fast >TAbort- <TAbort- <MAbort- >SERR- <PERR- INTx-
	Latency: 0, Cache Line Size: 64 bytes
	Interrupt: pin A routed to IRQ 127
	NUMA node: 0
	Region 0: Memory at a0000000 (32-bit, non-prefetchable) [size=256M]
	Region 1: Memory at b0000000 (32-bit, non-prefetchable) [size=64K]
	Capabilities: <access denied>
	Kernel driver in use: xdma
	Kernel modules: xdma
```

From the above output, we can see that there are three Alveo cards on the pcie bus. The first (at address 81:00.0) is running the Xilinx (factory) shell, while the other two (addresses c1:00 and c2:00) are running the SARAO BSP. We can see that the latter two cards have loaded the *xdma* kernel driver module, as expected. The other important part to note is the BAR size of Region 0, given in the square parenthese. This should be 256MBytes in size. If the memory size does not equal 256M while the *xdma* module is indeed loaded, it may mean that the running image has been built with a different BAR size, which is set in the Xilinx XDMA IP module in *Vivado* during development.

---

In order to ensure that the ***alveo-katcp-svr.py*** process has been started for each of the Alveo cards running the SARAO BSP, the linux process listing can be inspected as follows
```
$ ps fax | grep "[a]lveo-katcp-svr.py"
```
The output should look as follows for each of the Alveo cards:
```
 1714 ?        S      0:01 /usr/bin/python3.8 /root/.pex/unzipped_pexes/9406cbbd41ebb12539c12a574d2b2d45c83b5599 /opt/alveo/alveo-katcp-svr/alveo-katcp-svr.py --alveo alveo_1_u50 --workdir /tmp/alveo-katcp-svr-fs-0000-c1-00-0/ --port 7150 --card alveo_1_u50-501211207V5X -d
 ```

If the above process is not running, or there is not an instance for each of the Alveo cards (ie two Alveo cards require two alveo-katcp-svr instances in the process listing), the following command can be run in an attempt to start the processes.

```
sudo systemctl start alveo-katcp-svr.service
```

---

It is also useful to query a known register value to ensure that the pcie-to-axi bus is functioning as expected. For this the `pcimem` utility [reference: https://github.com/billfarrow/pcimem] can be used to read the REG_MAP_ID_REG register in the Alveo's *Card Management Solution (CMS)* Subsystem. This query is run at a lower level than the alveo-sw infrastructure, thereby bypassing it, and this is therefore a useful sanity check to verify the state of the Alveo card and *pcie* bus.

To do this, ensure that the Microblaze internal to the CMS is running. This is the case when the nRESET register is high (as readback below)
```
$ sudo pcimem /dev/xdma0_user 0x20000 w
/dev/xdma0_user opened.
Target offset is 0x20000, page size is 4096
mmap(0, 4096, 0x3, 0x1, 3, 0x20000)
PCI Memory mapped to address 0x7f547be04000.
0x20000: 0x00000001
```

Now we can check that we can communicate over the axi bus via pcie by confirming the register value equals 0x74736574
```
$ sudo pcimem /dev/xdma0_user 0x28000 w
/dev/xdma0_user opened.
Target offset is 0x28000, page size is 4096
mmap(0, 4096, 0x3, 0x1, 3, 0x28000)
PCI Memory mapped to address 0x7f2a89309000.
0x28000: 0x74736574
```
See CMS Product Guide for details: https://docs.xilinx.com/r/en-US/pg348-cms-subsystem/Register-Space

---

There are also various custom tools that have been scripted to display information about the Alveo cards. These can be found in `/opt/alveo/alveo-utils/` after installation. Example outputs are given below:

```
$ cd /opt/alveo/alveo-utils/

/opt/alveo/alveo-utils$ ./alveo-pci --help
usage: ./alveo-pci [--help] [--dev <xdma|xrt|all>]

/opt/alveo/alveo-utils$ ./alveo-pci --dev all
PCI Device @ 0000:81:00.0/xclmgmt33024
ID 0x500c
Region0 mem-size 32MiB
Region2 mem-size 128KiB
PCI Device @ 0000:c1:00.0/xdma0_user
ID 0x9031
Region0 mem-size 256MiB
Region1 mem-size 64KiB
```
The above output shows the details for two Alveo pcie cards. It shows the pcie address, the relevant device file, the device ID which has been set during development and lastly the BAR regions which are mapped into memory.

```
/opt/alveo/alveo-utils$ ./alveo-map
0000:c1:00.0/xdma0_user/501211207V5X
```
The output above gives the mapping of the pcie to card serial number for each of the Alveo cards. Note this is not the jtag serial number.  It also shows the device file used to interface with the axi-lite control bus.

```
/opt/alveo/alveo-utils$ ./alveo-serial /dev/xdma0_user
501211207V5X
```
The above shows the Alveo card serial number read via the relevant xdma*_user device file entry.
