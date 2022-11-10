#RvW, SARAO, 2022

ALVEOPATH="/opt/alveo/"
TBSFS="${ALVEOPATH}/alveo-tcpbs-fs/"
ALVEOUTILS="${ALVEOPATH}/alveo-utils/"
UDEVPATH="/etc/udev/rules.d/"
SYSTEMDPATH="/etc/systemd/system/"
PREFIX=usr/local
EXISTS=$(shell test -e ./alveo-linux-env/xdma-udev-rules/60-xdma.rules || echo 'NO')

install: .check .tcpborphserver3_install .kcpfpg_install .kcpcmd_install .pcimem_install .kcpmsg_install xdma_mod_install
	@test -d ${TBSFS} || mkdir -p ${TBSFS}
	cp -i ./alveo-tcpbs-fs/* ${TBSFS}
	cp -i ./alveo-linux-env/xdma-udev-rules/60-xdma.rules ./alveo-linux-env/xdma-udev-rules/alveo_namer.sh ${UDEVPATH}
	#install alveo-utils
	@test -d ${ALVEOUTILS} || mkdir -p ${ALVEOUTILS}
	cp -i ./alveo-utils/* ${ALVEOUTILS}
	#install tcpbs service
	cp -i ./alveo-linux-env/systemd-services/tcpbs.service ${SYSTEMDPATH}
	#install kernel module src and supporting build/service scripts
	test -d /usr/src/xdma-2020.2.2 || mkdir /usr/src/xdma-2020.2.2
	cp -r dma_ip_drivers/XDMA/linux-kernel/* /usr/src/xdma-2020.2.2
	cp alveo-linux-env/systemd-services/install-xdma.sh /usr/src/xdma-2020.2.2/.
	cp -i ./alveo-linux-env/systemd-services/xdma-install-check.service ${SYSTEMDPATH}
	systemctl enable xdma-install-check.service
	#install modprobe config
	cp -i ./alveo-linux-env/modprobe-configs/xdma.conf /etc/modprobe.d/xdma.conf
	#install alveo programming scripts
	install -D ./alveo-program/alveo-program.sh  ${ALVEOPATH}/alveo-program/alveo-program.sh
	install -D ./alveo-program/alveo-program.tcl ${ALVEOPATH}/alveo-program/alveo-program.tcl
	install -D ./alveo-program/alveo-pci-cfg ${ALVEOPATH}/alveo-program/alveo-pci-cfg

.check: .FORCE
ifeq ("$(EXISTS)","NO")
	$(error "First run ./configure to set up environment")
endif

.tcpborphserver3_install: .katcp_install
	prefix=${PREFIX} ${MAKE} -C katcp/tcpborphserver3/ install

.kcpfpg_install: .katcp_install
	prefix=${PREFIX} ${MAKE} -C katcp/fpg install
	ln -sf /usr/local/bin/kcpfpg /bin/kcpfpg

.kcpcmd_install: .katcp_install
	prefix=${PREFIX} ${MAKE} -C katcp/cmd install

.katcp_install:
	${MAKE} -C katcp/katcp/

.pcimem_install:
	${MAKE} -C pcimem/
	install pcimem/pcimem /usr/local/bin/

.kcpmsg_install: .katcp_install
	${MAKE} -C katcp/msg install

xdma_mod_install:
	${MAKE} -C dma_ip_drivers/XDMA/linux-kernel/xdma install
	${MAKE} -C dma_ip_drivers/XDMA/linux-kernel/xdma clean
	depmod -a
	modprobe xdma || insmod /lib/modules/$(shell uname -r)/extra/xdma.ko
	#test -d /usr/src/xdma-2020.2.2 || mkdir /usr/src/xdma-2020.2.2
	#cp -r dma_ip_drivers/XDMA/linux-kernel/* /usr/src/xdma-2020.2.2
	#cp alveo-linux-env/xdma-dkms/dkms.conf /usr/src/xdma-2020.2.2/.
	#dkms add -m xdma -v 2020.2.2
	#dkms build -m xdma -v 2020.2.2
	#dkms install -m xdma -v 2020.2.2

uninstall: .tcpborphserver3_uninstall .kcpfpg_uninstall .kcpcmd_uninstall
	$(RM) ${TBSFS}/*
	$(RM) ${ALVEOUTILS}/*

.tcpborphserver3_uninstall:
	prefix=${PREFIX} ${MAKE} -C katcp/tcpborphserver3/ uninstall

.kcpfpg_uninstall:
	prefix=${PREFIX} ${MAKE} -C katcp/fpg uninstall

.kcpcmd_uninstall:
	prefix=${PREFIX} ${MAKE} -C katcp/cmd uninstall

.kcpcmd_uninstall:
	prefix=${PREFIX} ${MAKE} -C katcp/msg uninstall


.PHONY: .check .pcimem_install .katcp_install .tcpborphserver3_install .kcpfpg_install .kcpcmd_install .tcpborphserver3_uninstall .kcpfpg_uninstall .kcpcmd_uninstall

.FORCE:
