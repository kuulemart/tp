#!/usr/bin/env bash

sudo pkill -f tp
pushd .
cd sql
psql postgres -f database.sql
popd
