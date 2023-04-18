# alveo-sw

This repo contains the supporting software infrstructure to control and monitor Alveos with the SARAO (CASPER) toolflow.
It runs in a linux environment and has been tested on Ubuntu 18.04. It also relies on the Alveo cards being "FLASHED" with the SARAO BSP. For further details on this, please see [Alveo Board Support Packages](https://github.com/ska-sa/alveo_bsp).
It furthermore expects a Xilinx *jtag* programmer to be used to configure (program) the Alveo with the "runtime" fpga images (ie *.fpg* or *.bit* files).

## Getting Started

From the shell, do the following steps:

Clone this repo
```
git clone https://github.com/ska-sa/alveo-sw.git
cd alveo-sw/
```

Initialise the *git* submodules
```
git submodule init
git submodule update
```

Now it is necessary to configure the infrastructure for the current host. This can be done by executing the following script on the command line
```
./configure
```

The software infrastructure relies on some python dependencies. Among these is the creation of a *python executable (pex)* environment which contains the dependencies required to run the python alveo katcp server. In order to generate this *pex* dependency, the following needs to be done

1. create a python3.8 virtual environment

```
python3.8 -m venv alveo_venv
```
2. launch the virtual environmnet
```
source alveo_venv/bin/activate
```
3. install the *pex* package
```
pip3.8 install pex
```
4. change directory to the *alveo-katcp-svr* directory and run *make*
```
cd alveo-katcp-svr
make
cd ..
```
5. deactivate the vrtual environment
```
deactivate
```

Now that the python dependencies have been built, the software infrastructure can be installed from within the parent *alveo-sw* directory
```
sudo make install
```
Reboot the host machine
```
sudo reboot
```
At this point, the Alveo supporting software infratructure shoud have be deployed and running. Some basic sanity checks to ensure that the required software is running correctly can be found in the [alveo-sw troubleshooting](./troubleshooting.md) guide.

The [casperfpga branch with alveo support](https://github.com/ska-sa/casperfpga/tree/devel#alveo-support) can now be used to connect to the Alveo cards.

---
## System startup
The following block diagram shows the various linux processes involved in launching the *alveo-katcp-svr*.
```
┌───────────────┐
│               │
│  linux boot   │
│               │
└──────┬────────┘
       │
       │
┌──────▼────────┐
│  modprobe     │ /etc/modprobe.d/xdma.conf
├───────────────┤
│   load xdma   │
│ kernel module │
└──────┬────────┘
       │
       │
       │
┌──────▼────────┐
│  udev         │ /etc/udev/rules.d/60-xdma.rules
├───────────────┤
│ configure /dev│
│ entries       │
└──────┬────────┘
       │
       │
       │
┌──────▼────────┐
│ systemd       │ /etc/systemd/system/alveo-katcp-svr.service
├───────────────┤
│launch alveo   │
│services       │
└──────┬────────┘
       │
       │
       │
┌──────▼────────┐
│               │
│alveo-katcp-svr│
│               │
└───────────────┘
```