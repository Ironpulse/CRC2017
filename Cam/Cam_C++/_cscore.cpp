
#include <pybind11/pybind11.h>
#include <pybind11/functional.h>
#include <pybind11/operators.h>
#include <pybind11/stl.h>
#include "release_gil.hpp"
namespace py = pybind11;

#include "cscore_oo.h"
using namespace cs;

#include <opencv2/opencv.hpp>

#include "ndarray_converter.h"
#include "wpiutil_converters.hpp"


PYBIND11_PLUGIN(_cscore) {

    NDArrayConverter::init_numpy();

    py::module m("_cscore");
    
    static int unused; // the capsule needs something to reference
    py::capsule cleanup(&unused, [](PyObject *) {
        // don't release gil until after calling this
        SetDefaultLogger(20 /* WPI_LOG_INFO */);
        
        // but this MUST release the gil, or deadlock may occur
        py::gil_scoped_release __release;
        CS_Destroy();
    });
    m.add_object("_cleanup", cleanup);
    
    // cscore_cpp.h
    
    py::class_<UsbCameraInfo> usbcamerainfo(m, "UsbCameraInfo");
    usbcamerainfo
      .def_readwrite("dev", &UsbCameraInfo::dev)
      .def_readwrite("path", &UsbCameraInfo::path)
      .def_readwrite("name", &UsbCameraInfo::name)
      .def("__repr__", [](UsbCameraInfo &__inst){
         return std::string("<UsbCameraInfo dev=") + std::to_string(__inst.dev) + " path=" + __inst.path + " name=" + __inst.name + ">";
       });
    
    py::class_<CS_VideoMode> cs_videomode(m, "_CS_VideoMode");
    
    py::class_<VideoMode, CS_VideoMode> videomode(m, "VideoMode");
    videomode
      .def(py::init<>())
      .def(py::init<cs::VideoMode::PixelFormat,int,int,int>())
      .def_property("pixelFormat",
            [](VideoMode &__inst) { return (cs::VideoMode::PixelFormat)__inst.pixelFormat; },
            [](VideoMode &__inst, cs::VideoMode::PixelFormat v) { __inst.pixelFormat = v; })
      .def_readwrite("width", &VideoMode::width)
      .def_readwrite("height", &VideoMode::height)
      .def_readwrite("fps", &VideoMode::fps);
      
    
    py::enum_<VideoMode::PixelFormat>(videomode, "PixelFormat")
      .value("kUnknown", VideoMode::PixelFormat::kUnknown)
      .value("kMJPEG", VideoMode::PixelFormat::kMJPEG)
      .value("kYUYV", VideoMode::PixelFormat::kYUYV)
      .value("kRGB565", VideoMode::PixelFormat::kRGB565)
      .value("kBGR", VideoMode::PixelFormat::kBGR)
      .value("kGray", VideoMode::PixelFormat::kGray);
    
    #define def_status_fn(n, N, T) def(n, [](T t) { py::gil_scoped_release __r; CS_Status s = 0; return N(t, &s); })
    
    m.def("getNetworkInterfaces", &GetNetworkInterfaces)
     .def_status_fn("getHttpCameraUrls", GetHttpCameraUrls, CS_Source)
     .def_status_fn("getMjpegServerPort", GetHttpCameraUrls, CS_Sink)
     .def("getMjpegServerListenAddress", &GetMjpegServerListenAddress)
     .def_status_fn("getUsbCameraPath", GetUsbCameraPath, CS_Source)
     .def("setLogger", &SetLogger);
     
    // cscore_oo.h

    py::class_<VideoProperty> videoproperty(m, "VideoProperty");
    videoproperty
      .def(py::init<>())
      .def("getName", py::release_gil(&VideoProperty::GetName))
      .def("getKind", py::release_gil(&VideoProperty::GetKind))
      .def("isBoolean", py::release_gil(&VideoProperty::IsBoolean))
      .def("isInteger", py::release_gil(&VideoProperty::IsInteger))
      .def("isString", py::release_gil(&VideoProperty::IsString))
      .def("isEnum", py::release_gil(&VideoProperty::IsEnum))
      .def("get", py::release_gil(&VideoProperty::Get))
      .def("set", py::release_gil(&VideoProperty::Set), py::arg("value"))
      .def("getMin", py::release_gil(&VideoProperty::GetMin))
      .def("getMax", py::release_gil(&VideoProperty::GetMax))
      .def("getStep", py::release_gil(&VideoProperty::GetStep))
      .def("getDefault", py::release_gil(&VideoProperty::GetDefault))
      .def("getString", py::release_gil((std::string (VideoProperty::*)() const)&VideoProperty::GetString))
      /*.def("GetString", [](VideoProperty &__inst) {
        llvm::SmallVectorImpl<char> buf;
        auto __ret = __inst.GetString(buf);
        return std::make_tuple(__ret, buf);
      })*/
      .def("setString", py::release_gil(&VideoProperty::SetString), py::arg("value"))
      .def("getChoices", py::release_gil(&VideoProperty::GetChoices))
      .def("getLastStatus", py::release_gil(&VideoProperty::GetLastStatus));
    
    py::enum_<VideoProperty::Kind>(videoproperty, "Kind")
      .value("kNone", VideoProperty::Kind::kNone)
      .value("kBoolean", VideoProperty::Kind::kBoolean)
      .value("kInteger", VideoProperty::Kind::kInteger)
      .value("kString", VideoProperty::Kind::kString)
      .value("kEnum", VideoProperty::Kind::kEnum);
    
    py::class_<VideoSource> videosource(m, "VideoSource");
    videosource
      .def(py::init<>())
      .def(py::init<cs::VideoSource>(), py::arg("source"))
      .def("getHandle", &VideoSource::GetHandle)
      .def(py::self == py::self)
      .def(py::self != py::self)
      .def("getKind", &VideoSource::GetKind,
          "Get the kind of the source")
      .def("getName", &VideoSource::GetName,
          "Get the name of the source. The name is an arbitrary identifier " 
          "provided when the source is created, and should be unique.")
      .def("getDescription", &VideoSource::GetDescription,
          "Get the source description.  This is source-kind specific.")
      .def("getLastFrameTime", &VideoSource::GetLastFrameTime,
          "Get the last time a frame was captured.")
      .def("isConnected", &VideoSource::IsConnected,
          "Is the source currently connected to whatever is providing the images?")
      .def("getProperty", py::release_gil(&VideoSource::GetProperty), py::arg("name"),
          "Get a property.\n\n"
          ":param name: Property name\n"
          ":returns: Property contents (VideoSource.Kind.kNone if no property with the given name exists)")
      .def("enumerateProperties", py::release_gil(&VideoSource::EnumerateProperties), "Enumerate all properties of this source")
      .def("getVideoMode", py::release_gil(&VideoSource::GetVideoMode), "Get the current video mode.")
      .def("setVideoMode", [](VideoSource &__inst, VideoMode mode) {
        py::gil_scoped_release __release;
        return __inst.SetVideoMode(mode);
    }, py::arg("mode"),
        "Set the video mode.\n\n"
        ":param mode: Video mode")
      .def("setVideoMode", [](VideoSource &__inst, VideoMode::PixelFormat pixelFormat, int width, int height, int fps) {
        py::gil_scoped_release __release;
        return __inst.SetVideoMode(pixelFormat, width, height, fps);
      }, py::arg("pixelFormat"), py::arg("width"), py::arg("height"), py::arg("fps"),
          "Set the video mode.\n\n"
          ":param pixelFormat: desired pixel format\n"
          ":param width: desired width\n"
          ":param height: desired height\n"
          ":param fps: desired FPS\n"
          ":returns: True if set successfully")
      .def("setPixelFormat", py::release_gil(&VideoSource::SetPixelFormat), py::arg("pixelFormat"),
          "Set the pixel format.\n\n"
          ":param pixelFormat: desired pixel format\n"
          ":returns: True if set successfully")
      .def("setResolution", py::release_gil(&VideoSource::SetResolution), py::arg("width"), py::arg("height"),
          "Set the resolution.\n\n"
          ":param width: desired width\n"
          ":param height: desired height\n"
          ":returns: True if set successfully")
      .def("setFPS", py::release_gil(&VideoSource::SetFPS), py::arg("fps"),
          "Set the frames per second (FPS).\n\n"
          ":param fps: desired FPS\n"
          ":returns: True if set successfully")
      .def("enumerateVideoModes", py::release_gil(&VideoSource::EnumerateVideoModes),
          "Enumerate all known video modes for this source.")
      .def("getLastStatus", py::release_gil(&VideoSource::GetLastStatus))
      .def("enumerateSinks", py::release_gil(&VideoSource::EnumerateSinks),
          "Enumerate all sinks connected to this source.\n\n"
          ":returns: list of sinks.")
      .def_static("enumerateSources", py::release_gil(&VideoSource::EnumerateSources),
          "Enumerate all existing sources.\n\n"
          ":returns: list of sources.");
      //.def("__repr__", [](VideoSource &__inst){
      //  std::stringstream id;
      //  id << (void const *)&__inst;
      //  return std::string("<VideoSource name=") + __inst.GetName() + " kind=" + std::to_string(__inst.GetKind()) + " at" + id.str() + ">";
      //});
    
    py::enum_<VideoSource::Kind>(videosource, "Kind")
      .value("kUnknown", VideoSource::Kind::kUnknown)
      .value("kUsb", VideoSource::Kind::kUsb)
      .value("kHttp", VideoSource::Kind::kHttp)
      .value("kCv", VideoSource::Kind::kCv);
    
    py::class_<VideoCamera, VideoSource> videocamera(m, "VideoCamera");
    videocamera
      .def(py::init<>())
      .def("setBrightness", py::release_gil(&VideoCamera::SetBrightness),
           py::arg("brightness"),
           "Set the brightness, as a percentage (0-100).")
      .def("getBrightness", py::release_gil(&VideoCamera::GetBrightness),
           "Get the brightness, as a percentage (0-100).")
      .def("setWhiteBalanceAuto", py::release_gil(&VideoCamera::SetWhiteBalanceAuto),
           "Set the white balance to auto.")
      .def("setWhiteBalanceHoldCurrent", py::release_gil(&VideoCamera::SetWhiteBalanceHoldCurrent),
           "Set the white balance to hold current.")
      .def("setWhiteBalanceManual", py::release_gil(&VideoCamera::SetWhiteBalanceManual),
           py::arg("value"),
           "Set the white balance to manual, with specified color temperature.")
      .def("setExposureAuto", py::release_gil(&VideoCamera::SetExposureAuto),
           "Set the exposure to auto aperature.")
      .def("setExposureHoldCurrent", py::release_gil(&VideoCamera::SetExposureHoldCurrent),
           "Set the exposure to hold current.")
      .def("setExposureManual", py::release_gil(&VideoCamera::SetExposureManual),
           py::arg("value"),
           "Set the exposure to manual, as a percentage (0-100).");
    
    py::enum_<VideoCamera::WhiteBalance>(videocamera, "WhiteBalance")
      .value("kFixedIndoor", VideoCamera::WhiteBalance::kFixedIndoor)
      .value("kFixedOutdoor1", VideoCamera::WhiteBalance::kFixedOutdoor1)
      .value("kFixedOutdoor2", VideoCamera::WhiteBalance::kFixedOutdoor2)
      .value("kFixedFluorescent1", VideoCamera::WhiteBalance::kFixedFluorescent1)
      .value("kFixedFlourescent2", VideoCamera::WhiteBalance::kFixedFlourescent2);
    
#ifdef __linux__
    py::class_<UsbCamera, VideoCamera> usbcamera(m, "UsbCamera");
    usbcamera
      .def(py::init<>())
      .def(py::init<llvm::StringRef,int>(),
          py::arg("name"), py::arg("dev"),
          "Create a source for a USB camera based on device number.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param dev: Device number (e.g. 0 for ``/dev/video0``)")
      .def(py::init<llvm::StringRef,llvm::StringRef>(),
          py::arg("name"), py::arg("path"),
          "Create a source for a USB camera based on device path.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param path: Path to device (e.g. ``/dev/video0`` on Linux)")
      .def_static("enumerateUsbCameras", py::release_gil(&UsbCamera::EnumerateUsbCameras),
          "Enumerate USB cameras on the local system.\n\n"
          ":returns: list of USB camera information (one for each camera)")
      .def("getPath", &UsbCamera::GetPath, "Get the path to the device.");
#endif

    py::class_<HttpCamera, VideoCamera> httpcamera(m, "HttpCamera");
    
    // this has to come before the constructor definition
    py::enum_<HttpCamera::HttpCameraKind>(httpcamera, "HttpCameraKind")
      .value("kUnknown", HttpCamera::HttpCameraKind::kUnknown)
      .value("kMJPGStreamer", HttpCamera::HttpCameraKind::kMJPGStreamer)
      .value("kCSCore", HttpCamera::HttpCameraKind::kCSCore)
      .value("kAxis", HttpCamera::HttpCameraKind::kAxis);
    
    httpcamera
      //.def(py::init<llvm::StringRef,llvm::StringRef,HttpCamera::HttpCameraKind>())
      //.def(py::init<llvm::StringRef,const char *,cs::HttpCamera::HttpCameraKind>())
      .def(py::init<llvm::StringRef,std::string,cs::HttpCamera::HttpCameraKind>(),
           py::arg("name"), py::arg("url"), py::arg("kind") = HttpCamera::HttpCameraKind::kUnknown,
          "Create a source for a MJPEG-over-HTTP (IP) camera.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param urls: Array of Camera URLs\n"
          ":param kind: Camera kind (e.g. kAxis)")
      .def(py::init<llvm::StringRef,llvm::ArrayRef<std::string>,HttpCamera::HttpCameraKind>(),
           py::arg("name"), py::arg("urls"), py::arg("kind") = HttpCamera::HttpCameraKind::kUnknown,
          "Create a source for a MJPEG-over-HTTP (IP) camera.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param urls: Array of Camera URLs\n"
          ":param kind: Camera kind (e.g. kAxis)")
      //.def(py::init<llvm::StringRef,std::initializer_list<T>,cs::HttpCamera::HttpCameraKind>())
      .def("getHttpCameraKind", py::release_gil(&HttpCamera::GetHttpCameraKind),
          "Get the kind of HTTP camera. "
          "Autodetection can result in returning a different value than the camera was created with.")
      .def("setUrls", py::release_gil((void (HttpCamera::*)(llvm::ArrayRef<std::string>))&HttpCamera::SetUrls),
           py::arg("urls"),
           "Change the URLs used to connect to the camera.")
      //.def("SetUrls", (void (HttpCamera::*)(std::initializer_list<T>))&HttpCamera::SetUrls)
      .def("getUrls", py::release_gil(&HttpCamera::GetUrls),
           "Get the URLs used to connect to the camera.");
    
    py::class_<AxisCamera, HttpCamera> axiscamera(m, "AxisCamera");
    axiscamera
      .def(py::init<llvm::StringRef,llvm::StringRef>(),
          py::arg("name"), py::arg("host"),
          "Create a source for a MJPEG-over-HTTP (IP) camera.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param urls: Array of Camera URLs\n"
          ":param kind: Camera kind (e.g. kAxis)")
      .def(py::init<llvm::StringRef,const char *>(),
          py::arg("name"), py::arg("host"),
          "Create a source for a MJPEG-over-HTTP (IP) camera.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param urls: Array of Camera URLs\n"
          ":param kind: Camera kind (e.g. kAxis)")
      .def(py::init<llvm::StringRef,std::string>(),
          py::arg("name"), py::arg("host"),
          "Create a source for a MJPEG-over-HTTP (IP) camera.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param urls: Array of Camera URLs\n"
          ":param kind: Camera kind (e.g. kAxis)")
      .def(py::init<llvm::StringRef,llvm::ArrayRef<std::string>>(),
          py::arg("name"), py::arg("host"),
          "Create a source for a MJPEG-over-HTTP (IP) camera.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param urls: Array of Camera URLs\n"
          ":param kind: Camera kind (e.g. kAxis)");
      //.def(py::init<llvm::StringRef,std::initializer_list<T>>());
    
    py::class_<CvSource, VideoSource> cvsource(m, "CvSource");
    cvsource
      .def(py::init<>())
      .def(py::init<llvm::StringRef,VideoMode>(),
          py::arg("name"), py::arg("mode"),
          "Create an OpenCV source.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param mode: Video mode being generated")
      .def(py::init<llvm::StringRef,VideoMode::PixelFormat,int,int,int>(),
          py::arg("name"), py::arg("pixelFormat"), py::arg("width"), py::arg("height"), py::arg("fps"),
          "Create an OpenCV source.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param pixelFormat: Pixel format\n"
          ":param width: width\n"
          ":param height: height\n"
          ":param fps: fps")
      .def("putFrame", [](CvSource &__inst, cv::Mat &image) {
        py::gil_scoped_release release;
        __inst.PutFrame(image);
      }, "Put an OpenCV image and notify sinks.\n\n"
          "Only 8-bit single-channel or 3-channel (with BGR channel order) images "
          "are supported. If the format, depth or channel order is different, use "
          "``cv2.convertTo()`` and/or ``cv2.cvtColor()`` to convert it first.\n\n"
          ":param image: OpenCV image")
      .def("notifyError", &CvSource::NotifyError,
          py::arg("msg"),
          "Signal sinks that an error has occurred.  This should be called instead "
          "of :meth:`putFrame` when an error occurs.")
      .def("setConnected", &CvSource::SetConnected,
          py::arg("connected"),
          "Set source connection status.  Defaults to true.\n\n"
          ":param connected: True for connected, false for disconnected")
      .def("setDescription", &CvSource::SetDescription,
          py::arg("description"),
          "Set source description.\n\n"
          ":param description: Description")
      .def("createProperty", py::release_gil(&CvSource::CreateProperty),
          py::arg("name"), py::arg("kind"), py::arg("minimum"), py::arg("maximum"), py::arg("step"), py::arg("defaultValue"), py::arg("value"),
          "Create a property.\n\n"
          ":param name: Property name\n"
          ":param kind: Property kind\n"
          ":param minimum: Minimum value\n"
          ":param maximum: Maximum value\n"
          ":param step: Step value\n"
          ":param defaultValue: Default value\n"
          ":param value: Current value\n\n"
          ":returns: Property\n")
      .def("setEnumPropertyChoices", py::release_gil((void (CvSource::*)(const VideoProperty &property, llvm::ArrayRef<std::string> choices))&CvSource::SetEnumPropertyChoices),
          py::arg("property"), py::arg("choices"),
          "Configure enum property choices.\n\n"
          ":param property: Property\n"
          ":param choices: Choices");
      /*.def("SetEnumPropertyChoices", [](CvSource &__inst, std::initializer_list<T> choices) {
        cs::VideoProperty property;
        auto __ret = __inst.SetEnumPropertyChoices(property, choices);
        return std::make_tuple(__ret, property);
    });*/
    
    py::class_<VideoSink> videosink(m, "VideoSink");
    videosink
      .def(py::init<>())
      .def(py::init<cs::VideoSink>(), py::arg("sink"))
      .def("getHandle", &VideoSink::GetHandle)
      .def(py::self == py::self)
      .def(py::self != py::self)
      .def("getKind", &VideoSink::GetKind,
          "Get the kind of the sink.")
      .def("getName", &VideoSink::GetName,
          "Get the name of the sink.  The name is an arbitrary identifier "
          "provided when the sink is created, and should be unique.")
      .def("getDescription", &VideoSink::GetDescription,
          "Get the sink description.  This is sink-kind specific.")
      .def("setSource", py::release_gil(&VideoSink::SetSource),
          py::arg("source"),
          "Configure which source should provide frames to this sink.  Each sink "
          "can accept frames from only a single source, but a single source can "
          "provide frames to multiple clients.\n\n"
          ":param source: Source")
      .def("getSource", py::release_gil(&VideoSink::GetSource),
          "Get the connected source.\n\n"
          ":returns: Connected source (empty if none connected).")
      .def("getSourceProperty", py::release_gil(&VideoSink::GetSourceProperty),
          "Get a property of the associated source.\n\n"
          ":param name: Property name\n"
          ":returns: Property (VideoSink.Kind.kNone if no property with the given name exists or no source connected)")
      .def("getLastStatus", &VideoSink::GetLastStatus)
      .def_static("enumerateSinks", py::release_gil(&VideoSink::EnumerateSinks),
          "Enumerate all existing sinks.\n\n"
          ":returns: list of sinks.");
    
    py::enum_<VideoSink::Kind>(videosink, "Kind")
      .value("kUnknown", VideoSink::Kind::kUnknown)
      .value("kMjpeg", VideoSink::Kind::kMjpeg)
      .value("kCv", VideoSink::Kind::kCv);
    
    py::class_<MjpegServer, VideoSink> mjpegserver(m, "MjpegServer");
    mjpegserver
      .def(py::init<>())
      .def(py::init<llvm::StringRef,llvm::StringRef,int>(),
          py::arg("name"), py::arg("listenAddress"), py::arg("port"),
          "Create a MJPEG-over-HTTP server sink.\n\n"
          ":param name: Sink name (arbitrary unique identifier)\n"
          ":param listenAddress: TCP listen address (empty string for all addresses)\n"
          ":param port: TCP port number")
      .def(py::init<llvm::StringRef,int>(),
          py::arg("name"), py::arg("port"),
          "Create a MJPEG-over-HTTP server sink.\n\n"
          ":param name: Sink name (arbitrary unique identifier)\n"
          ":param port: TCP port number")
      .def("getListenAddress", &MjpegServer::GetListenAddress, "Get the listen address of the server.")
      .def("getPort", &MjpegServer::GetPort, "Get the port number of the server.");
    
    py::class_<CvSink, VideoSink> cvsink(m, "CvSink");
    cvsink
      .def(py::init<>())
      .def(py::init<llvm::StringRef>(),
          py::arg("name"),
          "Create a sink for accepting OpenCV images. "
          ":meth:`grabFrame` must be called on the created sink to get each new image\n\n"
          ":param name: Source name (arbitrary unique identifier)")
      /*.def(py::init<llvm::StringRef,std::function<void(uint64_t)>>(),
          py::arg("name"), py::arg("processFrame"),
          "Create a sink for accepting OpenCV images in a separate thread. "
          "A thread will be created that calls the "
          "``processFrame`` callback each time a new frame arrives.\n\n"
          ":param name: Source name (arbitrary unique identifier)\n"
          ":param processFrame: Frame processing function; will be called with a "
          "time=0 if an error occurred.  processFrame should call :meth:`grabFrame`"
          "or :meth:`getError` as needed.")*/
      .def("setDescription", &CvSink::SetDescription,
          py::arg("description"),
          "Set sink description.\n\n"
          ":param description: Description")
      .def("grabFrame", [](CvSink &__inst, cv::Mat &image, double timeout) {
        py::gil_scoped_release release;
        auto __ret = __inst.GrabFrame(image, timeout);
        return std::make_tuple(__ret, image);
      }, py::arg("image"), py::arg("timeout") = 0.225,
          "Wait for the next frame and get the image. Times out (returning 0) after timeout seconds.\n"
          "The provided image will have three 8-bit channels stored in BGR order.\n\n"
          ":returns: Frame time, or 0 on error (call :meth:`getError` to obtain the error message), returned image")
      .def("grabFrameNoTimeout", [](CvSink &__inst, cv::Mat &image) {
          py::gil_scoped_release release;
          auto __ret = __inst.GrabFrameNoTimeout(image);
          return std::make_tuple(__ret, image);
        }, py::arg("image"),
          "Wait for the next frame and get the image. May block forever.\n"
          "The provided image will have three 8-bit channels stored in BGR order.\n\n"
          ":returns: Frame time, or 0 on error (call :meth:`getError` to obtain the error message), returned image")
      .def("getError", &CvSink::GetError,
           "Get error string.  Call this if :meth:`grabFrame` returns 0 to determine what the error is.")
      .def("setEnabled", &CvSink::SetEnabled,
          py::arg("enabled"),
          "Enable or disable getting new frames.\n"
          "Disabling will cause processFrame (for callback-based CvSinks) to not"
          " be called and :meth:`grabFrame` to not return.  This can be used to save"
          " processor resources when frames are not needed.");
    
    py::class_<RawEvent> rawevent(m, "RawEvent");
    rawevent
      .def_readonly("kind", &RawEvent::kind)
      .def_readonly("mode", &RawEvent::mode)
      .def_readonly("name", &RawEvent::name)
      .def_readonly("value", &RawEvent::value)
      .def_readonly("valueStr", &RawEvent::valueStr)
      .def_readonly("sourceHandle", &RawEvent::sourceHandle)
      .def_readonly("sinkHandle", &RawEvent::sinkHandle);
    
    py::enum_<RawEvent::Kind>(rawevent, "Kind")
      .value("kSourceCreated", RawEvent::Kind::kSourceCreated)
      .value("kSourceDestroyed", RawEvent::Kind::kSourceDestroyed)
      .value("kSourceConnected", RawEvent::Kind::kSourceConnected)
      .value("kSourceDisconnected", RawEvent::Kind::kSourceDisconnected)
      .value("kSourceVideoModesUpdated", RawEvent::Kind::kSourceVideoModesUpdated)
      .value("kSourceVideoModeChanged", RawEvent::Kind::kSourceVideoModeChanged)
      .value("kSourcePropertyCreated", RawEvent::Kind::kSourcePropertyCreated)
      .value("kSourcePropertyValueUpdated", RawEvent::Kind::kSourcePropertyValueUpdated)
      .value("kSourcePropertyChoicesUpdated", RawEvent::Kind::kSourcePropertyChoicesUpdated)
      .value("kSinkSourceChanged", RawEvent::Kind::kSinkSourceChanged)
      .value("kSinkCreated", RawEvent::Kind::kSinkCreated)
      .value("kSinkDestroyed", RawEvent::Kind::kSinkDestroyed)
      .value("kSinkEnabled", RawEvent::Kind::kSinkEnabled)
      .value("kSinkDisabled", RawEvent::Kind::kSinkDisabled)
      .value("kNetworkInterfacesChanged", RawEvent::Kind::kNetworkInterfacesChanged);
    
    py::class_<VideoEvent, RawEvent> videoevent(m, "VideoEvent");
    videoevent
      .def("getSource", &VideoEvent::GetSource)
      .def("getSink", &VideoEvent::GetSink)
      .def("getProperty", &VideoEvent::GetProperty);
      
    
    py::class_<VideoListener> videolistener(m, "VideoListener");
    videolistener
      .def(py::init<std::function<void(const VideoEvent&)>,int,bool>(),
          py::arg("callback"), py::arg("eventMask"), py::arg("immediateNotify"),
          "Create an event listener.\n\n"
          ":param callback: Callback function\n"
          ":param eventMask: Bitmask of VideoEvent.Kind values\n"
          ":param immediateNotify: Whether callback should be immediately called with"
          " a representative set of events for the current library state.");

    return m.ptr();
}
