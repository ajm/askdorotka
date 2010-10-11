#!/bin/bash

if [[ $# -eq 1 ]] ; then
    ln -sf $1.db annotations.db
    exit $?
fi

echo "Usage: $0 <db name>"
exit -1
