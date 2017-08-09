#!/usr/bin/env python3

import cscore as cs

camera = cs.UsbCamera("usbcam", 0)
camera.setVideoMode(cs.VideoMode.PixelFormat.kMJPEG, 320, 240, 30)

mjpegServer = cs.MjpegServer("httpserver", 8081)
mjpegServer.setSource(camera);

print("mjpg server listening at http://0.0.0.0:8081")
input("Press enter to exit...")