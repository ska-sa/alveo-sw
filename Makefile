TBSFS="/tmp/alveo/alveo-tcpbs-fs/"
UDEVPATH="/etc/udev/rules.d/"
PREFIX=usr/local
EXISTS=$(shell test -e ./alveo-linux-env/xdma-udev-rules/60-xdma.rules || echo 'NO')

install: .check .tcpborphserver3_install .kcpfpg_install .kcpcmd_install
	@test -d ${TBSFS} || mkdir -p ${TBSFS}
	@cp -i ./alveo-tcpbs-fs/* ${TBSFS}
	@cp -i ./alveo-linux-env/xdma-udev-rules/60-xdma.rules ./alveo-linux-env/xdma-udev-rules/alveo_namer.sh ${UDEVPATH}

.check: .FORCE
ifeq ("$(EXISTS)","NO")
	$(error "First run ./configure to set up environment")
endif

.tcpborphserver3_install: katcp
	prefix=${PREFIX} ${MAKE} -C katcp/tcpborphserver3/ install

.kcpfpg_install: katcp
	prefix=${PREFIX} ${MAKE} -C katcp/fpg install

.kcpcmd_install: katcp
	prefix=${PREFIX} ${MAKE} -C katcp/cmd install

.katcp_install:
	${MAKE} -C katcp/katcp/



uninstall: .tcpborphserver3_uninstall .kcpfpg_uninstall .kcpcmd_uninstall
	$(RM) ${TBSFS}/*

.tcpborphserver3_uninstall:
	prefix=${PREFIX} ${MAKE} -C katcp/tcpborphserver3/ uninstall

.kcpfpg_uninstall:
	prefix=${PREFIX} ${MAKE} -C katcp/fpg uninstall

.kcpcmd_uninstall:
	prefix=${PREFIX} ${MAKE} -C katcp/cmd uninstall



.PHONY: .check .katcp_install .tcpborphserver3_install .kcpfpg_install .kcpcmd_install .tcpborphserver3_uninstall .kcpfpg_uninstall .kcpcmd_uninstall

.FORCE:
