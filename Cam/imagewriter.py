
import os.path
import time
import threading

import cv2
import numpy as np

import logging
logger = logging.getLogger('cscore.storage')

class ImageWriter:
    '''
        Creates a thread that periodically writes images to a specified
        directory. Useful for looking at images after a match has 
        completed.
        
        The default location is ``/media/sda1/camera``. The folder
        ``/media/sda1`` is the default location that USB drives inserted into
        the RoboRIO are mounted at. The USB drive must have a directory in it
        named ``camera``.
        
        .. note:: It is recommended to only write images when something useful
                  (such as targeting) is happening, otherwise you'll end up
                  with a lot of images written to disk that you probably aren't
                  interested in. 
        
        Intended usage is::
        
            self.image_writer = ImageWriter()
            
            ..
            
            while True:
            
                img = .. 
                
                if self.logging_enabled:
                    self.image_writer.setImage(img)
    
    '''
    
    def __init__(self, *, location_root='/media/sda1/camera',
                          capture_period=0.5,
                          image_format='jpg'):
        '''
            :param location_root: Directory to write images to. A subdirectory
                                  with the current time will be created, and
                                  timestamped images will be written to the
                                  subdirectory.
            :param capture_period: How often to write images to disk
            :param image_format: File extension of files to write
        '''
        
        self.location_root = os.path.abspath(location_root)
        self.capture_period = capture_period
        self.image_format = image_format
        
        self.active = True
        self._location = None
        self.has_image = False
        self.size = None
        
        self.lock = threading.Condition()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        
    def setImage(self, img):
        '''
            Call this function when you wish to write the image to disk. Not
            every image is written to disk. Makes a copy of the image.
        
            :param img: A numpy array representing an OpenCV image
        '''
        
        if not self.active:
            return
        
        if self.size is None or self.size[0] != img.shape[0] or self.size[1] != img.shape[1]:
            h, w = img.shape[:2]
            self.size = (h, w)
            
            self.out1 = np.empty((h, w, 3), dtype=np.uint8)
            self.out2 = np.empty((h, w, 3), dtype=np.uint8)
        
        with self.lock:
            cv2.copyMakeBorder(img, 0, 0, 0, 0, cv2.BORDER_CONSTANT, value=(0,0,255), dst=self.out1)
            self.has_image = True
            self.lock.notify()
    
    @property
    def location(self):
        if self._location is None:
            
            # This assures that we only log when a USB memory stick is plugged in
            if not os.path.exists(self.location_root):
                raise IOError("Logging disabled, %s does not exist" % self.location_root)
            
            # Can't do this when program starts, time might be wrong. Ideally by now the DS
            # has connected, so the time will be correct
            self._location = self.location_root + '/%s' % time.strftime('%Y-%m-%d %H.%M.%S')
            logger.info("Logging to %s", self._location)
            os.makedirs(self._location, exist_ok=True)
            
        return self._location
    
    def _run(self):
        
        last = time.time()
        
        logger.info("Storage thread started")
        
        try:
        
            while True:
                with self.lock:
                    now = time.time()
                    while (not self.has_image) or (now - last) < self.capture_period:
                        self.lock.wait()
                        now = time.time()
                        
                    self.out2, self.out1 = self.out1, self.out2
                    self.has_image = False
                
                fname = '%s/%.2f.%s' % (self.location, now, self.image_format)
                cv2.imwrite(fname, self.out2)
                
                last = now
                
        except IOError as e:
            logger.error("Error logging images: %s", e)
            
        logger.warn("Storage thread exited")
        self.active = False
        