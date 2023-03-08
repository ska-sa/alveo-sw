#!/bin/bash

#RvW, SARAO, 2022

#removes the prefix xdma*_
echo ${1#*xdma[0-9]*_}
