#!/usr/bin/env bash

# Doing the pushd as a test of directory movement to try to be safer with the "rm"
pushd ../../osc/home:epage:$2/$1 && rm $1_*.dsc $1_*.tar.gz
popd

cp $3/$1_*.dsc $3/$1_*.tar.gz  ../../osc/home:epage:$2/$1

pushd ../../osc/home:epage:$2/$1

osc addremove && osc commit

popd
