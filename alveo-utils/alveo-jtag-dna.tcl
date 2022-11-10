set jtag_serial_number [lindex $argv 0]
set port_number [lindex $argv 1]

append url localhost: $port_number /xilinx_tcf/Xilinx/ $jtag_serial_number A
puts $url


open_hw_manager
exec hw_server -d -s tcp:localhost:$port_number -p0 -I2

connect_hw_server -url localhost:$port_number

open_hw_target $url
current_hw_device [lindex [get_hw_devices] 0]
refresh_hw_device -update_hw_probes false [current_hw_device]

append output "DNA read " [get_property REGISTER.EFUSE.FUSE_DNA [lindex [get_hw_device] 0]]
puts $output
