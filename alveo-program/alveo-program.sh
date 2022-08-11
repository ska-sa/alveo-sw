#!/usr/bin/sudo bash
#
# Created on: 12 April 2022
# Author: Mathews Chirindo
# Modified: RvW

# This script will start vivado in tcl mode and run a tcl script to program the alveo card.
# Arguments:
# $1 - the PCI address of the alveo card (use 'lspci -D -d 10ee: -vv' to get this)
# $2 - the .bit file to upload to the alveo

/opt/Xilinx/Vivado/2021.1/bin/vivado -mode batch -source alveo-program.tcl -tclargs $1 $2
