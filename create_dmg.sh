#!/usr/bin/env bash

# Wrapper around a wrapper around a thing that makes a wrapper 
# around my program which is a wrapper for a python script

# Usage: create_dmg.sh path_to_dmg.dmg path_to_src/

create-dmg \
--volname "Locatorator" \
--window-size 350 100 \
--icon-size 64 \
--text-size 12 \
--icon Locatorator.app 72 85 \
--app-drop-link 225 85 \
$1 \
$2