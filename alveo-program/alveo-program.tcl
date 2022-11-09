# Created on: 12 April 2022
# Author: Mathews Chirindo
#
# Modified: RvW, SARAO, 2022


# create two lookup structures for mapping the jtag serial number and port number to the pci addr
set lookup_jtag [dict create pci jtag]
set lookup_port [dict create pci port]

#open the config mapping file
set fp [open "alveo-pci-cfg" r]

#split the file data into lines
set data [split [read $fp] "\n"]

close $fp

#for each line
foreach line $data {
  if { [string length $line] != 0 } {
    #split into columns
    set cols [split $line " "]
    #puts "[lindex $cols 0]"
    #puts "[lindex $cols 1]"
    #puts "[lindex $cols 2]"
    dict append lookup_jtag [lindex $cols 0] [lindex $cols 1]
    dict append lookup_port [lindex $cols 0] [lindex $cols 2]
  }
}

puts $lookup_jtag
puts $lookup_port

if { [dict exists $lookup_jtag [lindex $argv 0]] != 1 ||  [dict exists $lookup_port [lindex $argv 0]] != 1  } {
  puts "Invalid PCI ID [lindex $argv 0]"
  exit 2
}

if { [file exists [lindex $argv 1]] != 1 } {
  puts "Cannot access [lindex $argv 1]"
  exit 3
}

set jtag_serial_number [dict get $lookup_jtag [lindex $argv 0]]
set port_number [dict get $lookup_port [lindex $argv 0]]
append url localhost: $port_number /xilinx_tcf/Xilinx/ $jtag_serial_number A
puts $url

open_hw_manager
exec hw_server -d -s tcp:localhost:$port_number -p0 -I1
connect_hw_server -url localhost:$port_number
open_hw_target $url
current_hw_device [lindex [get_hw_devices] 0]
refresh_hw_device -update_hw_probes false [current_hw_device]
# set_property PARAM.FREQUENCY 10000000 [current_hw_target]
puts "will attempt to program alveo with [lindex $argv 1]"
set_property PROGRAM.FILE [lindex $argv 1] [current_hw_device]
program_hw_devices [current_hw_device]
