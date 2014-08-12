#!/usr/bin/env bash

# kill connections
sudo pkill -f tp
pushd .
cd sql
psql postgres -f database.sql
popd
