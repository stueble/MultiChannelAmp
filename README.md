# MultiChannelAmpDaemon
A small python based daemon to control the sound cards of type KAB9 and the power supply of my 24 channel multi channel amp based on the states of a couple of sqeezelite players.

The code was interactively generated with https://claude.ai as a test case. Although some iterations had been necessary to get it finally working, I am so far happy with the result. To continue the development using AI, you can start with the current specification at [doc/Specification.md](doc/Specification.md)

## Installation

Copy files to
* ```/usr/local/bin/MultiChannelAmpDaemon.py``` - Main daemon (executable)
* ```/usr/local/bin/amp_callback.py``` - Callback script (executable)

Optional
* ```/etc/udev/rules.d/90-usb-audio.rules``` - Ensure that sound card ids will not change, see [config/udev/](config/udev/)

## Usage example

```bash
bashsqueezelite -n kitchen \
  -S "/usr/local/bin/amp_callback.py kitchen" \
  -o hw:4,0 &
```

