#!/usr/bin/sudo bash
#
# Created on: 12 April 2022
# Author: Mathews Chirindo
# 
# This script will start vivado in tcl mode and run a tcl script to program the alveo card. 1 argument, $1 is passed as the PCI ID where the specific alveo cardis siting in the server.

/opt/Xilinx/Vivado/2021.1/bin/vivado -mode batch -source alveo-program.tcl -tclargs $1

#cd /sys/bus/pci/devices/
#echo 1 > 0000\0f\00.0/remove
#echo 1 > 0000\0f\00.1/remove
#cd ..
#echo 1 > rescan


