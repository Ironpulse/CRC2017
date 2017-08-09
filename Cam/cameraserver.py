#*----------------------------------------------------------------------------*/
#* Copyright (c) FIRST 2016-2017. All Rights Reserved.                        */
#* Open Source Software - may be modified and shared by FRC teams. The code   */
#* must be accompanied by the FIRST BSD license file in the root directory of */
#* the project.                                                               */
#*----------------------------------------------------------------------------*/

# TODO: should this be distributed here, or with WPILib? My gut says here, 
# because it's useful here too.

import re
import socket
import threading

import cscore
from cscore import VideoEvent, VideoProperty, VideoSink, VideoSource

import logging
logger = logging.getLogger('cscore.cserver')

from networktables import NetworkTables

__all__ = ['CameraServer', 'VideoException']

class VideoException(Exception):
    pass

class CameraServer:
    """Singleton class for creating and keeping camera servers.
    
    This is a higher level wrapper around the cscore functionality, and also
    publishes camera information to NetworkTables so that dashboards can easily
    find and display the camera streams.
    """
    
    kBasePort = 1181
    kPublishName = "/CameraPublisher"

    @classmethod
    def getInstance(cls):
        """Get the CameraServer instance."""
        try:
            return cls._server
        except AttributeError:
            cls._server = cls()
            return cls._server
        
    @staticmethod
    def enableLogging(level=logging.INFO):
        cscore.enableLogging(level=level)
        
    def _getSourceTable(self, source):
        return self._tables.get(source.getHandle())
    
    @staticmethod
    def _makeSourceValue(source):
        kind = source.getKind()
        if kind == VideoSource.Kind.kUsb:
            return "usb:" + cscore.getUsbCameraPath(source.getHandle())
        
        elif kind == VideoSource.Kind.kHttp:
            urls = cscore.getHttpCameraUrls(source.getHandle())
            if urls:
                return "ip:" + urls[0]
            else:
                return "ip:"
            
        elif kind == VideoSource.Kind.kCv:
            # FIXME: Should be "cv:", but LabVIEW dashboard requires "usb:".
            # https://github.com/wpilibsuite/allwpilib/issues/407
            return "usb:"
        
        else:
            return "unknown:"
    
    @staticmethod
    def _makeStreamValue(address, port):
        return "mjpg:http://%s:%s/?action=stream" % (address, port)
    
    def _getSinkStreamValues(self, sink):
        with self._mutex:
            # Ignore all but MjpegServer
            if sink.getKind() != VideoSink.Kind.kMjpeg:
                return []
            
            # Get port
            port = sink.getPort()
    
            # Generate values
            values = []
            listenAddress = sink.getListenAddress()
            if listenAddress:
                # If a listen address is specified, only use that
                values.append(self._makeStreamValue(listenAddress, port))
            else:
                # Otherwise generate for hostname and all interface addresses
                values.append(self._makeStreamValue(socket.gethostname() + ".local", port))
                for addr in self._addresses:
                    if addr == "127.0.0.1":
                        continue    # ignore localhost
                    
                    values.append(self._makeStreamValue(addr, port))
    
            return values
    
    def _getSourceStreamValues(self, source):
        with self._mutex:
            # Ignore all but HttpCamera
            if source.getKind() != VideoSource.Kind.kHttp:
                return []
            
            # Generate values
            values = ['mjpg:%s' % v for v in source.getUrls()]
            
            # Look to see if we have a passthrough server for this source
            sourceHandle = source.getHandle()
            for sink in self._sinks.values():
                sinkSourceHandle = sink.getSource().getHandle()
                if sourceHandle == sinkSourceHandle \
                    and sink.getKind() == VideoSink.Kind.kMjpeg:
                    # Add USB-only passthrough
                    port = sink.getPort()
                    values.append(self._makeStreamValue("172.22.11.2", port))
                    break
            
            return values
    
    def _updateStreamValues(self):
        with self._mutex:
            # Over all the sinks...
            for sink in self._sinks.values():
    
                # Get the source's subtable (if none exists, we're done)
                source = sink.getSource()
                sourceHandle = source.getHandle()
                if not sourceHandle:
                    continue
                
                table = self._getSourceTable(source)
                if table is not None:
                    # Don't set stream values if this is a HttpCamera passthrough
                    if source.getKind() == VideoSource.Kind.kHttp:
                        continue
                    
                    # Set table value
                    values = self._getSinkStreamValues(sink)
                    if values:
                        table.putStringArray("streams", values)
            
            # Over all the sources...
            for source in self._sources.values():
                # Get the source's subtable (if none exists, we're done)
                table = self._getSourceTable(source)
                if table is not None:
                    # Set table value
                    values = self._getSourceStreamValues(source)
                    if values:
                        table.putStringArray("streams", values)
    
    _pixelFormats = {
        cscore.VideoMode.PixelFormat.kMJPEG: "MJPEG",
        cscore.VideoMode.PixelFormat.kYUYV: "YUYV",
        cscore.VideoMode.PixelFormat.kRGB565: "RGB565",
        cscore.VideoMode.PixelFormat.kBGR: "BGR",
        cscore.VideoMode.PixelFormat.kGray: "Gray",
    }
    
    @classmethod
    def _pixelFormatToString(cls, pixelFormat):
        return cls._pixelFormats.get(pixelFormat, "Unknown")
    
    _pixelFmtStrings = {
        "MJPEG": cscore.VideoMode.PixelFormat.kMJPEG,
        "mjpeg": cscore.VideoMode.PixelFormat.kMJPEG,
        "JPEG": cscore.VideoMode.PixelFormat.kMJPEG,
        "jpeg": cscore.VideoMode.PixelFormat.kMJPEG,
        
        "YUYV": cscore.VideoMode.PixelFormat.kYUYV,
        "yuyv": cscore.VideoMode.PixelFormat.kYUYV,
        
        "RGB565": cscore.VideoMode.PixelFormat.kRGB565,
        "rgb565": cscore.VideoMode.PixelFormat.kRGB565,
        
        "BGR": cscore.VideoMode.PixelFormat.kBGR,
        "bgr": cscore.VideoMode.PixelFormat.kBGR,
        
        "GRAY": cscore.VideoMode.PixelFormat.kGray,
        "Gray": cscore.VideoMode.PixelFormat.kGray,
        "gray": cscore.VideoMode.PixelFormat.kGray,
    }
        
    @classmethod
    def _pixelFormatFromString(cls, pixelFormatStr):
        return cls._pixelFmtStrings.get(pixelFormatStr, cscore.VideoMode.PixelFormat.kUnknown)
    
    
    _reMode = re.compile("(?P<width>[0-9]+)\\s*x\\s*(?P<height>[0-9]+)\\s+(?P<format>.*?)\\s+"
                         "(?P<fps>[0-9.]+)\\s*fps")

    @classmethod
    def _videoModeFromString(cls, modeStr):
        '''Construct a video mode from a string description.'''
        matcher = cls._reMode.match(modeStr)
        if not matcher:
            return cscore.VideoMode(cscore.VideoMode.PixelFormat.kUnknown, 0, 0, 0)
        
        pixelFormat = cls._pixelFormatFromString(matcher.group("format"))
        width = int(matcher.group("width"))
        height = int(matcher.group("height"))
        fps = int(float(matcher.group("fps")))
        return cscore.VideoMode(pixelFormat, width, height, fps)
    

    @classmethod
    def _videoModeToString(cls, mode):
        """Provide string description of video mode.
           The returned string is "{widthx{height:format:fpsfps".
        """
        return '%sx%s %s %s fps' % (
            mode.width, mode.height,
            cls._pixelFormatToString(mode.pixelFormat),
            mode.fps)
    
    @classmethod
    def _getSourceModeValues(cls, source):
        modes = source.enumerateVideoModes()
        return [cls._videoModeToString(mode) for mode in modes]

    @staticmethod
    def _putSourcePropertyValue(table, event, isNew):
        if event.name.startswith("raw_"):
            name = "RawProperty/" + event.name[4:]
            infoName = "RawPropertyInfo/" + event.name[4:]
        else:
            name = "Property/" + event.name
            infoName = "PropertyInfo/" + event.name
        
        prop = event.getProperty()
        propertyKind = prop.getKind()

        if propertyKind == VideoProperty.Kind.kBoolean:
            if isNew:
                table.setDefaultBoolean(name, event.value != 0)
            else:
                table.putBoolean(name, event.value != 0)
                
        elif propertyKind in [VideoProperty.Kind.kInteger, VideoProperty.Kind.kEnum]:
            if isNew:
                table.setDefaultNumber(name, event.value)
                table.putNumber(infoName + "/min", prop.getMin())
                table.putNumber(infoName + "/max", prop.getMax())
                table.putNumber(infoName + "/step", prop.getStep())
                table.putNumber(infoName + "/default", prop.getDefault())
            else:
                table.putNumber(name, event.value)
            
        elif propertyKind == VideoProperty.Kind.kString:
            if isNew:
                table.setDefaultString(name, event.valueStr)
            else:
                table.putString(name, event.valueStr)
    
    def __init__(self):
        self._mutex = threading.RLock()
        
        self._defaultUsbDevice = 0 # type: AtomicInteger
        self._primarySourceName = None # type: String
        
        self._sources = {}  # type: Dict[str, VideoSource]
        self._sinks = {}  # type: Dict[str, VideoSink]
        self._tables = {}  # type: Dict[int, networktables.NetworkTable]
        self._publishTable = NetworkTables.getTable(self.kPublishName)
        self._nextPort = self.kBasePort
        self._addresses = []

        # We publish sources to NetworkTables using the following structure:
        # "/CameraPublisher/{Source.Name/" - root
        # - "source" (string): Descriptive, prefixed with type (e.g. "usb:0")
        # - "streams" (string array): URLs that can be used to stream data
        # - "description" (string): Description of the source
        # - "connected" (boolean): Whether source is connected
        # - "mode" (string): Current video mode
        # - "modes" (string array): Available video modes
        # - "Property/{Property" - Property values
        # - "PropertyInfo/{Property" - Property supporting information

        # Listener for video events
        def _ve(e):
            try:
                self._onVideoEvent(e)
            except Exception:
                logger.exception("Unhandled exception in _onVideoEvent")
        
        self._videoListener = cscore.VideoListener(_ve, 0x4fff, True)

        # Listener for NetworkTable events
        # .. figures this uses the one API we don't really support
        self._nt = NetworkTables.getGlobalTable()
        NetworkTables._api.addEntryListener(self.kPublishName + "/", self._onTableChange,
                                            NetworkTables.NotifyFlags.IMMEDIATE | NetworkTables.NotifyFlags.UPDATE)

    def _onVideoEvent(self, event):
        source = event.getSource()
        
        if event.kind == VideoEvent.Kind.kSourceCreated:
            # Create subtable for the camera
            table = self._publishTable.getSubTable(event.name)
            with self._mutex:
                self._tables[source.getHandle()] = table

            table.putString("source", self._makeSourceValue(source))
            table.putString("description", source.getDescription())
            table.putBoolean("connected", source.isConnected())
            table.putStringArray("streams", self._getSourceStreamValues(source))
            
            try:
                mode = source.getVideoMode() # type: cscore.VideoMode
                table.setDefaultString("mode", self._videoModeToString(mode))
                table.putStringArray("modes", self._getSourceModeValues(source))
            except VideoException:
                # Do nothing. Let the other event handlers update this if there is an error.
                pass

        elif event.kind == VideoEvent.Kind.kSourceDestroyed:
            table = self._getSourceTable(source)
            if table is not None:
                table.putString("source", "")
                table.putStringArray("streams", [])
                table.putStringArray("modes", [])

        elif event.kind == VideoEvent.Kind.kSourceConnected:
            table = self._getSourceTable(source)
            if table is not None:
                # update the description too (as it may have changed)
                table.putString("description", source.getDescription())
                table.putBoolean("connected", True)

        elif event.kind == VideoEvent.Kind.kSourceDisconnected:
            table = self._getSourceTable(source)
            if table is not None:
                table.putBoolean("connected", False)

        elif event.kind == VideoEvent.Kind.kSourceVideoModesUpdated:
            table = self._getSourceTable(source)
            if table is not None:
                table.putStringArray("modes", self._getSourceModeValues(source))

        elif event.kind == VideoEvent.Kind.kSourceVideoModeChanged:
            table = self._getSourceTable(source)
            if table is not None:
                table.putString("mode", self._videoModeToString(event.mode))

        elif event.kind == VideoEvent.Kind.kSourcePropertyCreated:
            table = self._getSourceTable(source)
            if table is not None:
                self._putSourcePropertyValue(table, event, True)

        elif event.kind == VideoEvent.Kind.kSourcePropertyValueUpdated:
            table = self._getSourceTable(source)
            if table is not None:
                self._putSourcePropertyValue(table, event, False)

        elif event.kind == VideoEvent.Kind.kSourcePropertyChoicesUpdated:
            table = self._getSourceTable(source)
            if table is not None:
                prop = event.getProperty()
                choices = prop.getChoices()  # type: List[str]
                table.putStringArray("PropertyInfo/" + event.name + "/choices", choices)

        elif event.kind in (VideoEvent.Kind.kSinkSourceChanged, VideoEvent.Kind.kSinkCreated, VideoEvent.Kind.kSinkDestroyed):
            self._updateStreamValues()

        elif event.kind == VideoEvent.Kind.kNetworkInterfacesChanged:
            self._addresses = cscore.getNetworkInterfaces()

    def _onTableChange(self, key, value, flags):
        relativeKey = key[len(self.kPublishName) + 1:]  # type: str

        # get source (sourceName/...)
        subKeyIndex = relativeKey.find('/')
        if subKeyIndex == -1:
            return

        sourceName = relativeKey[0:subKeyIndex]
        source = self._sources.get(sourceName)  # type: VideoSource
        if source is None:
            return

        # get subkey
        relativeKey = relativeKey[subKeyIndex + 1:]

        # handle standard names
        if relativeKey == "mode":
            # Reset to current mode
            self._nt.putString(key, self._videoModeToString(source.getVideoMode()))
            return
        elif relativeKey.startswith("Property/"):
            propName = relativeKey[9:]
        elif relativeKey.startswith("RawProperty/"):
            propName = relativeKey[12:]
        else:
            return    # ignore

        # everything else is a property
        # .. reset to current setting
        prop = source.getProperty(propName)  # type: VideoProperty
        if prop.isBoolean():
            self._nt.putBoolean(key, prop.get() != 0)
        elif prop.isInteger() or prop.isEnum():
            self._nt.putNumber(key, prop.get())
        elif prop.isString():
            self._nt.putString(key, prop.getString())

    def startAutomaticCapture(self, *, dev=None, name=None, path=None, camera=None):
        """Start automatically capturing images to send to the dashboard.
        
        You should call this method to see a camera feed on the dashboard.
        If you also want to perform vision processing on the roboRIO, use
        :meth:`getVideo` to get access to the camera images.
        
        :param dev: If specified, the device number to use
        :param name: If specified, the name to use for the camera (dev must be specified)
        :param path: If specified, device path (e.g. "/dev/video0") of the camera
        :param camera: If specified, an existing camera object to use
        
        :returns: USB Camera object, or the camera argument
        :rtype: :class:`cscore.VideoSource` object
        
        The following argument combinations are accepted -- all argument must be specified
        as keyword arguments:
        
        * (no args)
        * dev
        * dev, name
        * name, path
        * camera
        
        If no arguments are specified, a USB Camera from device 0 is created.
        
        .. note:: USB Cameras are not available on all platforms. If it is not
                  available on your platform, :exc:`.VideoException` is thrown
        
        """
        
        if camera is not None:
            assert dev is None and name is None and path is None
        else:
            if not hasattr(cscore, 'UsbCamera'):
                raise VideoException("USB Camera support not available on this platform!")
            
            if dev is not None:
                assert camera is None
                assert path is None
                arg = dev
                
            elif path is not None:
                assert camera is None
                assert dev is None
                assert name is not None
                arg = path
            
            else:
                arg = 0
            
            if name is None:
                name = 'USB Camera %d' % arg
            
            camera = cscore.UsbCamera(name, arg)
        
        self.addCamera(camera)
        server = self.addServer(name="serve_" + camera.getName())
        server.setSource(camera)
        
        return camera
    
    def addAxisCamera(self, host, name="Axis Camera"):
        """Adds an Axis IP camera.
        
        :param host: String or list of camera host IPs/DNS names
        :param name: optional name of camera
        
        :returns: Axis camera object
        :rtype: :class:`cscore.AxisCamera`
        """
        camera = cscore.AxisCamera(name, host)
        # Create a passthrough MJPEG server
        return self.startAutomaticCapture(camera=camera)

    def getVideo(self, *, name=None, camera=None):
        """Get OpenCV access to specified camera. This allows you to
        get images from the camera for image processing.
        
        :param name: Name of camera to retrieve video for
        :param camera: Camera object
        
        :returns: CvSink object corresponding to camera
        :rtype: :class:`cscore.CvSink`
        
        All arguments must be specified as keyword arguments. The following
        combinations are permitted:
        
        * (no args)
        * name
        * camera
        
        If there are no arguments, then this will retrieve access to the
        primary camera. No arguments will fail if a camera feed has not already
        been added via :meth:`startAutomaticCapture` or :meth:`addCamera`
        
        """
        with self._mutex:
            if camera is not None:
                assert name is None
                
            else:
                if name is None:
                    name = self._primarySourceName
                
                camera = self._sources.get(name)
        
            if camera is None:
                raise VideoException("no camera available")
            
            name = "opencv_" + camera.getName()
            
            sink = self._sinks.get(name)  # type: cscore.VideoSink
            if sink is not None:
                kind = sink.getKind()
                if kind != VideoSink.Kind.kCv:
                    raise VideoException("expected OpenCV sink, but got %s (name: %s)" % (kind, name))
                
                return sink
        
        newsink = cscore.CvSink(name)
        newsink.setSource(camera)
        
        with self._mutex:
            self._sinks[name] = newsink
        
        return newsink
    
    def putVideo(self, name, width, height):
        """Create a MJPEG stream with OpenCV input. This can be called to pass custom
        annotated images to the dashboard.
        
        :param name: Name to give the stream
        :param width: Width of the image being sent
        :param height: Height of the image being sent
        
        :returns: CvSource object that you can publish images to
        :rtype: :class:`cscore.CvSource`
        """
        source = cscore.CvSource(name, cscore.VideoMode.PixelFormat.kMJPEG, width, height, 30)
        self.startAutomaticCapture(camera=source)
        return source
    
    def addServer(self, *, name=None, port=None, server=None):
        """Adds a MJPEG server
        
        :param name: Server name
        :param port: Port of server (if None, use next available port)
        :param server: 
        
        :returns: server object
        :rtype: :class:`cscore.VideoSink`
        
        All arguments must be specified as keyword arguments. The following
        combinations are accepted:
        
        * name
        * name, port
        * server
        
        """
        
        with self._mutex:
            if server is not None:
                assert name is None and port is None
                
            else:
                assert name is not None
                
                if port is None:
                    port = self._nextPort
                    self._nextPort += 1
                    
                server = cscore.MjpegServer(name, port)
            
            sname = server.getName()
            sport = server.getPort()
            
            logger.info("CameraServer '%s' listening on port %s", sname, sport)
            
            self._sinks[sname] = server
            return server
    
    def removeServer(self, name):
        """Removes a server by name.
        
        :param name: Server name
        """
        with self._mutex:
            self._sinks.pop(name, None)
            
    def getServer(self, name=None):
        """Get server for the primary camera feed
        
        This is only valid to call after a camera feed has been added
        with :meth:`startAutomaticCapture` or :meth:`addServer`
        
        :param name: Name of server or None
        
        :returns: server object
        """
        with self._mutex:
            if name is None:
                if self._primarySourceName is None:
                    raise VideoException("No primary video source defined")
                name = 'serve_' + self._primarySourceName 
                
            server = self._sources.get(name)
            if server is None:
                raise VideoException("server %s is not available" % server)
            
            return server
    
    def addCamera(self, camera):
        """Adds an already created camera.
        
        :param camera: Camera object
        :type camera: :class:`cscore.VideoSource`
        """
        name = camera.getName()
        with self._mutex:
            if self._primarySourceName is None:
                self._primarySourceName = name
            
            if name in self._sources:
                raise KeyError("Camera with name '%s' already exists" % name)
            
            self._sources[name] = camera
    
    def removeCamera(self, name):
        """Removes a camera by name.
        
        :param name: Camera name
        """
        with self._mutex:
            self._sources.pop(name, None)

    def waitForever(self):
        """Infinitely loops until the process dies"""
        import time
        while True:
            time.sleep(1)
