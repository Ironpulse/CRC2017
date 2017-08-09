#!/usr/bin/env python3

import sys
import time

import cscore as cs

def _usage():
    print("Usage: settings.py camera [prop val] ... -- [prop val]", file=sys.stderr)
    print("  Example: settings.py brightness 30 raw_contrast 10", file=sys.stderr)

def main():
    
    if not hasattr(cs, 'UsbCamera'):
        print("ERROR: This platform does not currently have cscore UsbCamera support")
        exit(1)
    
    if len(sys.argv) < 3:
        _usage()
        exit(1)
        
    try:
        cid = int(sys.argv[1])
    except ValueError:
        print("ERROR: Expected first argument to be a number, got '%s'" % sys.argv[1])
        _usage()
        exit(2)
        
    camera = cs.UsbCamera("usbcam", cid)
    
    # Set prior to connect
    argc = 2
    propName = None
    
    for arg in sys.argv[argc:]:
        argc += 1
        if arg == '--':
            break
        
        if propName is None:
            propName = arg
        else:
            try:
                propVal = int(arg)
            except ValueError:
                camera.getProperty(propName).setString(arg)
            else:
                camera.getProperty(propName).set(propVal)
                
            propName = None
    
    # Wait to connect
    while not camera.isConnected():
        time.sleep(0.010)
    
    # Set rest
    for arg in sys.argv[argc:]:
        if propName is None:
            propName = arg
        else:
            try:
                propVal = int(arg)
            except ValueError:
                camera.getProperty(propName).setString(arg)
            else:
                camera.getProperty(propName).set(propVal)
                
            propName = None
    
    # Print settings
    print("Properties:")
    for prop in camera.enumerateProperties():
        kind = prop.getKind()
        if kind == cs.VideoProperty.Kind.kBoolean:
            print(prop.getName(), "(bool) value=%s default=%s" % (prop.get(), prop.getDefault()))
        elif kind == cs.VideoProperty.Kind.kInteger:
            print(prop.getName(), "(int): value=%s min=%s max=%s step=%s default=%s" % \
            (prop.get(), prop.getMin(), prop.getMax(), prop.getStep(), prop.getDefault()))
        elif kind == cs.VideoProperty.Kind.kString:
            print(prop.getName(), "(string):", prop.getString())
        elif kind == cs.VideoProperty.Kind.kEnum:
            print(prop.getName(), "(enum): value=%s" % prop.get())
            for i, choice in enumerate(prop.getChoices()):
                if choice:
                    print("    %s: %s" % (i, choice))

if __name__ == '__main__':
    main()