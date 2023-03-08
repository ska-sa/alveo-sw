#!/bin/bash

#RvW, SARAO, 2022

set -e

#$1 jtag serial
#$2 port

test -n "$1"
test -n "$2"

list=$(ls -Art1 hwserver-$1-$2* 2>/dev/null)

count=$(echo ${list} | tr ' ' '\n' | wc -l)

if test ${count} -ge 5; then
  rm $(echo ${list} | tr ' ' '\n' | head -1)
fi
