# MultiChannelAmpDaemon
A small python based daemon to control the sound cards of type KAB9 and the power supply of my 24 channel multi channel amp based on the states of a couple of sqeezelite players.

## Installation

## Usage example

```bash
bashsqueezelite -n wohnzimmer \
  -S "/usr/local/bin/amp_callback.py wohnzimmer" \
  -o hw:4,0 &
``
