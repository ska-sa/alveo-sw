#!/usr/bin/env bash

#RvW, SARAO,2022

set -e

test ! -e /lib/modules/$(uname -r)/extra/xdma.ko || { echo "$(date) xdma kernel module already exists" && exit 1; }

echo "$(date) installing xdma kernel module"

cd $(dirname "$0")/xdma

make install

depmod -a

insmod /lib/modules/$(uname -r)/extra/xdma.ko

make clean

cd -
