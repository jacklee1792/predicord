#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
python -m black --target-version=py310 --line-length=88 $SCRIPT_DIR/..
