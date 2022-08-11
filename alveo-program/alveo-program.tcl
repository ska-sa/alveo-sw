# Created on: 12 April 2022
# Author: Mathews Chirindo
#
# This script is started from tcpborphserver as a subprocess. It should only be run on hfghost1 server
# (at least at the moment) wherein the JTAG programming cables should be fived to their corresponding
# alveo cards
#

# create a dictinary (lookup) for PCI IDs and JTAG cable serial numbers
set lookup [dict create PCI_ID "JTAG" 0000:c1:00.0 "500202A20EDA" 0000:81:00.0 "21770297400J"]

open_hw_manager
switch [lindex $argv 0] {
    # PCI ID: 0000:c1:00.0
     0000:c1:00.0 {
           exec hw_server -d -s tcp:localhost:3150 -p0 -I20
           connect_hw_server -url localhost:3150
	   set jtag_serial_number [dict get $lookup [lindex $argv 0]]
	   append jtag_serial_number "A"
	   append url "localhost:3150/xilinx_tcf/Xilinx/" $jtag_serial_number
           open_hw_target $url
     }
     # PCI ID: 0000:81:00.0
     0000:81:00.0 {
           exec hw_server -d -s tcp:localhost:3160 -p0 -I20
           connect_hw_server -url localhost:3160
	   set jtag_serial_number [dict get $lookup [lindex $argv 0]]
	   append jtag_serial_number "A"
	   append url "localhost:3160/xilinx_tcf/Xilinx/" $jtag_serial_number
           open_hw_target url
     }
         default {
             puts "Invalid PCI ID, [lindex $argv 0]"
             exit 2
     }
}
current_hw_device [lindex [get_hw_devices] 0]
refresh_hw_device -update_hw_probes false [current_hw_device]
# set_property PARAM.FREQUENCY 10000000 [current_hw_target]
set_property PROGRAM.FILE /lib/firmware/tcpborphserver.bit [current_hw_device]
program_hw_devices [current_hw_device]
