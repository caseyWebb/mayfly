#!/usr/bin/env bash

if [ ! -d "/Volumes/CIRCUITPY" ]; then
  echo "Error: /Volumes/CIRCUITPY is not mounted"
  exit 1
fi

echo "Copying src/circuitpy/ to /Volumes/CIRCUITPY..."

rsync -avhP src/circuitpy/ /Volumes/CIRCUITPY

echo "Done!"