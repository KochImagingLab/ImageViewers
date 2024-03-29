#! /usr/bin/env python3
""" 
QtImageViewer.py: PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.

"""

import os.path
import os
import sys
from PIL import ImageQt
from PIL import Image, ImageDraw

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import nibabel as nib
import SimpleITK as sitk
import scipy.io
import PyQt5

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QT_VERSION_STR, QLineF, QRegExp
from PyQt5.QtGui import QImage, QPixmap, QPainterPath, QPainter, QPen, QColor, QIntValidator, QTransform, QBrush
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QGroupBox,\
                            QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QLineEdit,QPushButton,\
                            QGraphicsLineItem, QScrollBar, QCheckBox, QComboBox, QAbstractItemView, QLabel
from PyQt5.QtWidgets import QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

__author__ = ""
__version__ = ""


class CrosshairWindow(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes1 = self.fig.add_subplot(211)
        self.axes1.set_title("Vertical Profile")
        self.axes2 = self.fig.add_subplot(212)
        self.axes2.set_title("Horizontal Profile")
        self.fig.subplots_adjust(hspace=0.8)
        super(CrosshairWindow, self).__init__(self.fig)
        
class ThruPlaneWindow(FigureCanvasQTAgg):

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig2 = Figure(figsize=(width, height), dpi=dpi)
        self.plt1 = self.fig2.add_subplot(321)
        self.plt2 = self.fig2.add_subplot(322)
        
        self.plt1_2 = self.fig2.add_subplot(323)
        self.plt2_2 = self.fig2.add_subplot(324)
        
        self.plt3 = self.fig2.add_subplot(313)
        
        self.fig2.subplots_adjust(hspace=0.8, wspace=0.5)
            

        super(ThruPlaneWindow, self).__init__(self.fig2)



class QtImageViewer(QGraphicsView):
    """ PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.

    Displays a QImage or QPixmap (QImage is internally converted to a QPixmap).
    To display any other image format, you must first convert it to a QImage or QPixmap.

    Some useful image format conversion utilities:
        qimage2ndarray: NumPy ndarray <==> QImage    (https://github.com/hmeine/qimage2ndarray)
        ImageQt: PIL Image <==> QImage  (https://github.com/python-pillow/Pillow/blob/master/PIL/ImageQt.py)

    Mouse interaction:
        Left mouse button drag: Pan image.
        Right mouse button drag: Zoom box.
        Right mouse button doubleclick: Zoom to show entire image.
    """

    # Mouse button signals emit image scene (x, y) coordinates.
    # !!! For image (row, column) matrix indexing, row = y and column = x.
    leftMouseButtonPressed = pyqtSignal(float, float)
    rightMouseButtonPressed = pyqtSignal(float, float)
    leftMouseButtonReleased = pyqtSignal(float, float)
    rightMouseButtonReleased = pyqtSignal(float, float)
    leftMouseButtonDoubleClicked = pyqtSignal(float, float)
    rightMouseButtonDoubleClicked = pyqtSignal(float, float)
    
    def __init__(self):
        QGraphicsView.__init__(self)

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        
        
        #set the focus to this viewer
        self.setFocusPolicy(Qt.StrongFocus)

        # Store a local handle to the scene's current image pixmap.
        self._pixmapHandle = None

        # Image aspect ratio mode.
        # !!! ONLY applies to full image. Aspect ratio is always ignored when zooming.
        #   Qt.IgnoreAspectRatio: Scale image to fit viewport.
        #   Qt.KeepAspectRatio: Scale image to fit inside viewport, preserving aspect ratio.
        #   Qt.KeepAspectRatioByExpanding: Scale image to fill the viewport, preserving aspect ratio.
        self.aspectRatioMode = Qt.KeepAspectRatio

        # Scroll bar behaviour.
        #   Qt.ScrollBarAlwaysOff: Never shows a scroll bar.
        #   Qt.ScrollBarAlwaysOn: Always shows a scroll bar.
        #   Qt.ScrollBarAsNeeded: Shows a scroll bar only when zoomed.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Stack of QRectF zoom boxes in scene coordinates.
        self.zoomStack = []
        
        # -------------------
        self.__fileName = None
        self.__imageData = None
        self.__pixeldims = None
        self.__pixelspacing = None
        self.__imgorientation = 1
        self.__curSlice = 0
        
        # -------------------
        self.__crossshow = False
        self.__lineX = QLineF()
        self.__lineY = QLineF() 
        
        # -------------------
        self.__crosshair = 0
        self.__thruPlane = 0
        self.__vert = 0
        self.__horiz = 0
        self.__flipX = False
        self.__flipY = False
        self.__rotateAngle = 270
        
        # -------------------
        self.__winlevel = 0
        self.__winwidth = 256

        # Flags for enabling/disabling mouse interaction.
        self.canZoom = True
        self.canPan = True

    def hasImage(self):
        """ Returns whether or not the scene contains an image pixmap.
        """
        return self._pixmapHandle is not None

    def clearImage(self):
        """ Removes the current image pixmap from the scene if it exists.
        """
        if self.hasImage():
            self.scene.removeItem(self._pixmapHandle)
            self._pixmapHandle = None

    def pixmap(self):
        """ Returns the scene's current image pixmap as a QPixmap, or else None if no image exists.
        :rtype: QPixmap | None
        """
        if self.hasImage():
            return self._pixmapHandle.pixmap()
        return None

    def image(self):
        """ Returns the scene's current image pixmap as a QImage, or else None if no image exists.
        :rtype: QImage | None
        """
        if self.hasImage():
            return self._pixmapHandle.pixmap().toImage()
        return None

    def setImage(self, image):
        """ Set the scene's current image pixmap to the input QImage or QPixmap.
        Raises a RuntimeError if the input image has type other than QImage or QPixmap.
        :type image: QImage | QPixmap
        """
        if type(image) is QPixmap:
            pixmap = image
        elif type(image) is QImage:
            pixmap = QPixmap.fromImage(image)
        else:
            raise RuntimeError("ImageViewer.setImage: Argument must be a QImage or QPixmap.")
        
        if self.hasImage():
            self._pixmapHandle.setPixmap(pixmap)
        else:
            self._pixmapHandle = self.scene.addPixmap(pixmap)
            
        self.setSceneRect(QRectF(pixmap.rect()))  # Set scene size to image size.
#         self.setSliceOrientation(self.__imgorientation)
        self.updateViewer()
        
        
    def buildCrosshairPopup(self, data):
        self.ch = CrosshairWindow(self, width=5, height=4, dpi=100)

        if self.__imgorientation == 1:
            horizArr = self.__imageData[:,0,self.getCurSlice()]
            vertArr = self.__imageData[0,:,self.getCurSlice()]
            horizArr2 = data[:,0,self.getCurSlice()]
            vertArr2 = data[0,:,self.getCurSlice()]
        elif self.__imgorientation == 2:   
            horizArr = self.__imageData[:,self.getCurSlice(),0]
            vertArr = self.__imageData[0,self.getCurSlice(),:]
            horizArr2 = data[:,self.getCurSlice(),0]
            vertArr2 = data[0,self.getCurSlice(),:]
        elif self.__imgorientation == 3:
            horizArr = self.__imageData[self.getCurSlice(),:,0]
            vertArr = self.__imageData[self.getCurSlice(),0,:]
            horizArr2 = data[self.getCurSlice(),:,0]
            vertArr2 = data[self.getCurSlice(),0,:]
        else:
            print("ERROR: Invlaid plane")
            
        self.ch.axes1.plot(vertArr, label="Left")
        self.ch.axes2.plot(horizArr, label="Left")
        self.ch.axes1.plot(vertArr2, label="Right")
        self.ch.axes2.plot(horizArr2, label="Right")
        self.ch.show()
        
        self.ch.axes1.legend(loc='upper right')
        self.ch.axes2.legend(loc='upper right')
        
        self.display_VertLine(self.getVertVal())
        self.display_HorizLine(self.getHorizVal())
        
        
        
            
    def clearCrosshairPopup(self):
        self.ch.close()
        self.__crosshair = 0
        self.scene.removeItem(self.HLine)
        self.scene.removeItem(self.VLine)
        self.setHorizVal(0)
        self.setVertVal(0)
        if(self.__thruPlane == 2):
            self.__thruPlane = 0
            self.tp.close()
            
    def clearCrosshairs(self):
        self.scene.removeItem(self.HLine)
        self.scene.removeItem(self.VLine)
        self.setHorizVal(0)
        self.setVertVal(0)
        if(self.__thruPlane == 2):
            self.__thruPlane = 0
        
    def setCrosshair(self, value, data):
        
        if self.__imageData is not None:
            self.__crosshair = value
            if(value == 2):
                self.buildCrosshairPopup(data)
            else:
                self.clearCrosshairPopup()
        else:
            return 0
        
            
    def buildThruPlanePopup(self, data):
        self.tp = ThruPlaneWindow(self, width=5, height=4, dpi=100)

        if self.__imgorientation == 1:
            data1 = np.rot90(self.__imageData[:,self.getHorizVal(),:])
            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:]) 
            data1_2 = np.rot90(data[:,self.getHorizVal(),:])
            data2_2 = np.rot90(data[self.getVertVal(),:,:]) 
            data3 = self.__imageData[self.getVertVal(),self.getImgHeight()-1-self.getHorizVal(),:]
            data3_2 = data[self.getVertVal(),self.getImgHeight()-1-self.getHorizVal(),:]
        elif self.__imgorientation == 2:
            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:])
            data1_2 = np.rot90(data[:,:,self.getHorizVal()])
            data2_2 = np.rot90(data[self.getVertVal(),:,:])
            data3 = self.__imageData[self.getVertVal(),:,self.getImgHeight()-1-self.getHorizVal()]
            data3_2 = data[self.getVertVal(),:,self.getImgHeight()-1-self.getHorizVal()]
        elif self.__imgorientation == 3:
            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
            data2 = np.rot90(self.__imageData[:,self.getVertVal(),:])
            data1_2 = np.rot90(data[:,:,self.getHorizVal()])
            data2_2 = np.rot90(data[:,self.getVertVal(),:])
            data3 = self.__imageData[:,self.getVertVal(),self.getImgHeight()-1-self.getHorizVal()]
            data3_2 = data[:,self.getVertVal(),self.getImgHeight()-1-self.getHorizVal()]


        self.tp.plt1.imshow(data1, aspect='auto')
        self.tp.plt2.imshow(data2, aspect='auto')
        self.tp.plt1_2.imshow(data1_2, aspect='auto')
        self.tp.plt2_2.imshow(data2_2, aspect='auto')
        self.tp.plt3.plot(data3, label="Left")
        self.tp.plt3.plot(data3_2, label="Right")
        self.tp.plt3.legend(loc='upper right')
        
        self.tp.plt3.set_title("Through-Plane Profile")
        self.tp.plt3.set_xlabel("Slice Number")
        self.tp.plt3.set_xlim([0, int(self.getSliceMax())])
        
        self.tp.show()
        
        self.display_VertLine(self.getVertVal())
        self.display_HorizLine(self.getHorizVal())
        
        
    def updateThroughPlane(self, data):
        if self.__imgorientation == 1:
            data1 = np.rot90(self.__imageData[:,self.getHorizVal(),:])
            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:]) 
            data1_2 = np.rot90(data[:,self.getHorizVal(),:])
            data2_2 = np.rot90(data[self.getVertVal(),:,:]) 
            data3 = self.__imageData[self.getVertVal(),self.getImgHeight()-1-self.getHorizVal(),:]
            data3_2 = data[self.getVertVal(),self.getImgHeight()-1-self.getHorizVal(),:]
        elif self.__imgorientation == 2:
            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:])
            data1_2 = np.rot90(data[:,:,self.getHorizVal()])
            data2_2 = np.rot90(data[self.getVertVal(),:,:])
            data3 = self.__imageData[self.getVertVal(),:,self.getImgHeight()-1-self.getHorizVal()]
            data3_2 = data[self.getVertVal(),:,self.getImgHeight()-1-self.getHorizVal()]
        elif self.__imgorientation == 3:
            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
            data2 = np.rot90(self.__imageData[:,self.getVertVal(),:])
            data1_2 = np.rot90(data[:,:,self.getHorizVal()])
            data2_2 = np.rot90(data[:,self.getVertVal(),:])
            data3 = self.__imageData[:,self.getVertVal(),self.getImgHeight()-1-self.getHorizVal()]
            data3_2 = data[:,self.getVertVal(),self.getImgHeight()-1-self.getHorizVal()]

        
        self.tp.plt1.clear()
        self.tp.plt2.clear()
        self.tp.plt1_2.clear()
        self.tp.plt2_2.clear()
        self.tp.plt3.clear()

        self.tp.plt1.imshow(data1, aspect='auto')
        self.tp.plt2.imshow(data2, aspect='auto')
        self.tp.plt1_2.imshow(data1_2, aspect='auto')
        self.tp.plt2_2.imshow(data2_2, aspect='auto')
        self.tp.plt3.plot(data3, label="Left")
        self.tp.plt3.plot(data3_2, label="Right")
        self.tp.plt3.legend(loc='upper right')
        
        
        self.tp.plt3.set_title("Through-Plane Profile")
        self.tp.plt3.set_xlabel("Slice Number")
        self.tp.plt3.set_xlim([0, int(self.getSliceMax())])
        
        self.tp.draw()
        
    
    def clearThruPlanePopup(self):
        self.tp.close()
            
            
    def setThruPlane(self, value, data):
        self.__thruPlane = value
        if(value == 2):
            self.buildThruPlanePopup(data)
        else:
            self.clearThruPlanePopup()
            
    def updateVerticalProfile(self, value, data):
        self.setVertVal(value)
        
        if self.__imgorientation == 1:
            vertArr = self.__imageData[value,:,self.getCurSlice()]
            vertArr2 = data[value,:,self.getCurSlice()]
        elif self.__imgorientation == 2:   
            vertArr = self.__imageData[value,self.getCurSlice(),:]
            vertArr2 = data[value,self.getCurSlice(),:]
        elif self.__imgorientation == 3:
            vertArr = self.__imageData[self.getCurSlice(),value,:]
            vertArr2 = data[self.getCurSlice(),value,:]
        else:
            print("ERROR: Invlaid plane")
            

        self.ch.axes1.clear()
        self.ch.axes1.set_title("Vertical Profile")
        self.ch.axes1.plot(vertArr, label="Left")
        self.ch.axes1.plot(vertArr2, label="Right")
        self.ch.axes1.legend(loc='upper right')
        self.ch.draw()
        
        if(self.__thruPlane == 2):
            self.updateThroughPlane(data)
        
        self.display_VertLine(value)
        
    def updateHorizontalProfile(self, value, data):
        self.setHorizVal(value)
        
        if self.__imgorientation == 1:
            horizArr = self.__imageData[:,self.getImgHeight()-1-value,self.getCurSlice()]
            horizArr2 = data[:,self.getImgHeight()-1-value,self.getCurSlice()]
        elif self.__imgorientation == 2:   
            horizArr = self.__imageData[:,self.getCurSlice(),self.getImgHeight()-1-value]
            horizArr2 = data[:,self.getCurSlice(),self.getImgHeight()-1-value]
        elif self.__imgorientation == 3:
            horizArr = self.__imageData[self.getCurSlice(),:,self.getImgHeight()-1-value]
            horizArr2 = data[self.getCurSlice(),:,self.getImgHeight()-1-value]
        else:
            print("ERROR: Invlaid plane")
        
        self.ch.axes2.clear()
        self.ch.axes2.set_title("Horizontal Profile")
        self.ch.axes2.plot(horizArr, label="Left")
        self.ch.axes2.plot(horizArr2, label="Right")
        self.ch.axes2.legend(loc='upper right')
        self.ch.draw()
        
        if(self.__thruPlane == 2):
            self.updateThroughPlane(data)
        self.display_HorizLine(value)
        
         
    def display_VertLine(self, value):
        try:
            self.scene.removeItem(self.VLine)
        except:
            pass
        self.VLine = self.scene.addLine(value, 0, value, self.getImgHeight(), QPen(Qt.red))
    
         
    def display_HorizLine(self, value):
        try:
            self.scene.removeItem(self.HLine)
        except:
            pass
        self.HLine = self.scene.addLine(0, value, self.getImgWidth(), value, QPen(Qt.green))

        
    def getHorizVal(self):
        return self.__horiz
    
    def getVertVal(self):
        return self.__vert
        
    def setHorizVal(self, value):
        self.__horiz = value
    
    def setVertVal(self, value):
        self.__vert = value

    
    def setWindowLevel(self, value):
        self.__winlevel = value
        self.imgWindowChange(self.__winlevel, self.__winwidth)
        
    def setWindowWidth(self, value):
        self.__winwidth = value 
        self.imgWindowChange(self.__winlevel, self.__winwidth)
    
    def getWindowLevel(self):
        return self.__winlevel
        
    def getWindowWidth(self):
        return self.__winwidth        
        
    def imgWindowChange(self, winowlevel, windowwidth):
        self.__winlevel = winowlevel
        self.__winwidth = windowwidth
        
        self.setSlice(self.__curSlice)            
    
    def imgProcessing(self, data):
        # display levels
        nlevels = 256    #int8
        bpp = 8
        
        y_min = 0
        y_max = nlevels -1 
        
        dout = ((data - (self.__winwidth/2+self.__winlevel - 0.5))/(self.__winwidth - 1) + 0.5) * (y_max-y_min) + y_min
        
        dout[dout<y_min] = y_min
        dout[dout>y_max] = y_max
        
        return dout.astype(np.uint8) 
    
    def resampleImage(self, spacing=None,fill_value=0):
        
        sitk_image = sitk.GetImageFromArray(self.__imageData)
        sitk_image.SetSpacing([float(self.__pixelspacing[2]), \
                               float(self.__pixelspacing[1]), \
                               float(self.__pixelspacing[0])])
        
        num_dim = sitk_image.GetDimension()
        orig_pixelid = sitk_image.GetPixelIDValue()
        orig_origin = sitk_image.GetOrigin()
        orig_direction = sitk_image.GetDirection()
        orig_spacing = sitk_image.GetSpacing()
        orig_size = np.array(sitk_image.GetSize(), dtype=np.int)
    
        if spacing is None:
            min_spacing = min(orig_spacing)
            new_spacing = [min_spacing]*num_dim
        else:
            new_spacing = [float(s) for s in spacing]
    
        sitk_interpolator = sitk.sitkLinear
    
        new_size = orig_size*(np.array(orig_spacing)/np.array(new_spacing))
        new_size = np.ceil(new_size).astype(np.int) #  Image dimensions are in integers
        new_size = [int(s) for s in new_size] #  SimpleITK expects lists, not ndarrays
    
        resample_filter = sitk.ResampleImageFilter()
    
        resampled_sitk_image = resample_filter.Execute(sitk_image,
                                                       new_size,
                                                       sitk.Transform(),
                                                       sitk_interpolator,
                                                       orig_origin,
                                                       new_spacing,
                                                       orig_direction,
                                                       fill_value,
                                                       orig_pixelid)
    
        self.__imageData = np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[2,1,0])
        self.__pixeldims = self.__imageData.shape
        self.__pixelspacing = [new_spacing,new_spacing,new_spacing]
        self.__winlevel = self.__imageData.min()
        self.__winwidth = self.__imageData.max()-self.__imageData.min()         
        self.__imgorientation = 1 # x-y
        self.__curSlice = self.__pixeldims[2]//2
        self.setSlice(self.__curSlice) 
        
    def setCrossShow(self, value):
        if value == 0:
            self.__crossshow = False
        else:
            self.__crossshow = True
    
    def getImageMaximum(self):
        if self.__imageData is not None:
            return self.__imageData.max()
        else:
            return 0
        
    def getImageMinimum(self):
        if self.__imageData is not None:
            return self.__imageData.min()
        else:
            return 0  
        
    def getWinLevelRange(self):
        if self.__imageData is None:
            return [0,1]
        else:
#             return [self.getSliceMin(), self.getSliceMax()]
            return [self.__imageData.min(), self.__imageData.max()]  
    
    def getWinWidthRange(self):
        if self.__imageData is None:
            return [0,1]
        else:
#             return [0, self.getSliceMax()-self.getSliceMin()] 
            return [self.__imageData.min(), self.__imageData.max()]   
            
    def setSliceOrientation(self, orientation):
        if orientation == 1:
            self.__imgorientation = 1
            self.setSliceOrientationToXY()
        elif orientation == 2:   
            self.__imgorientation = 2
            self.setSliceOrientationToXZ()
        else:
            self.__imgorientation = 3
            self.setSliceOrientationToYZ()
    
    def setSliceOrientationToXY(self):
        self.__imgorientation = 1
        if (self.__imageData is not None):
            self.__curSlice = self.__pixeldims[2]//2
            self.setSlice(self.__curSlice) 
    
    def setSliceOrientationToXZ(self):
        self.__imgorientation = 2
        if (self.__imageData is not None):
            self.__curSlice = self.__pixeldims[1]//2
            self.setSlice(self.__curSlice) 
    
    def setSliceOrientationToYZ(self):
        self.__imgorientation = 3
        if (self.__imageData is not None):
            self.__curSlice = self.__pixeldims[0]//2 
            self.setSlice(self.__curSlice) 
        
    def setFlipX(self, value):
        self.__flipX = value
        self.setSlice(self.__curSlice) 
    
    def setFlipY(self, value):
        self.__flipY = value
        self.setSlice(self.__curSlice)   
    
    def setRotateAngle(self, value):
        self.__rotateAngle = value
        self.setSlice(self.__curSlice)  
        
    def getRotateAngle(self):
        return self.__rotateAngle
    
    def getCurSlice(self):
        return self.__curSlice
    
    def getImgOrientation(self):
        return self.__imgorientation
    
    def getCrosshair(self):
        return self.__crosshair
       
    def get_qimage(self,image:np.ndarray):
#         assert (np.max(image) <= 256)
        image8 = image.astype(np.uint8, order='C', casting='unsafe')
        height, width = image8.shape
        bytesPerLine = width
        image = QImage(image8.data, width, height, bytesPerLine, QImage.Format_Indexed8)
        return image
 
    def setSliceOrig(self, slice):
        if (self.__imageData is not None) and (slice>=self.getSliceMin() and slice<=self.getSliceMax()):
            self.__curSlice = slice
            if self.__imgorientation == 1:   #x-y
#                 localData = self.__imageData[:,:,slice]
                data = self.imgProcessing(self.__imageData[:,:,slice])  
                qimage = self.get_qimage(data)
#                 qimage = qimage.mirrored(self.__flipX, self.__flipY)
                rotate = QTransform()
                rotate.rotate(self.__rotateAngle)
                qimg = qimage.transformed(rotate)
                self.setImage(qimg)                
            elif self.__imgorientation == 2:  #x-z
                data = self.imgProcessing(self.__imageData[:,slice,:])              
                qimage = self.get_qimage(data)
#                 qimage = qimage.mirrored(self.__flipX, self.__flipY)   
                rotate = QTransform()
                rotate.rotate(self.__rotateAngle)
                qimg = qimage.transformed(rotate)                
                self.setImage(qimg) 
            else:                          #y-z
                data = self.imgProcessing(self.__imageData[slice,:,:])              
                qimage = self.get_qimage(data)
#                 qimage = qimage.mirrored(self.__flipX, self.__flipY)   
                rotate = QTransform()
                rotate.rotate(self.__rotateAngle)
                qimg = qimage.transformed(rotate)                
                self.setImage(qimg)   
                
                
    def setSlice(self, slice):
        if (self.__imageData is not None) and (slice>=self.getSliceMin() and slice<=self.getSliceMax()):
            self.__curSlice = slice
            if self.__imgorientation == 1:   #x-y
                data = self.imgProcessing(self.__imageData[:,:,slice]) 
                imgInt = (data/np.max(data)*255).astype(np.int)
                
                imgRGB_Mapped = np.stack([imgInt,imgInt,imgInt],axis=2)
                im = Image.fromarray((imgRGB_Mapped * 255).astype(np.uint8))
                
                data2 = im.tobytes("raw","RGB")
                qim = QImage(data2, im.size[0], im.size[1], QImage.Format_RGB888)
                rotate = QTransform()
                rotate.rotate(270)
                qimg = qim.transformed(rotate)
                pix = QPixmap.fromImage(qimg)
                self.setImage(pix)   
            elif self.__imgorientation == 2:  #x-z
                data = self.imgProcessing(self.__imageData[:,slice,:])  
                imgInt = (data/np.max(data)*255).astype(np.int)
                
                imgRGB_Mapped = np.stack([imgInt,imgInt,imgInt],axis=2)
                im = Image.fromarray((imgRGB_Mapped * 255).astype(np.uint8))

                data2 = im.tobytes("raw","RGB")
                qim = QImage(data2, im.size[0], im.size[1], QImage.Format_RGB888)
                rotate = QTransform()
                rotate.rotate(270)
                qimg = qim.transformed(rotate)
                pix = QPixmap.fromImage(qimg)
                self.setImage(pix)   
            else:                          #y-z
                data = self.imgProcessing(self.__imageData[slice,:,:])    
                imgInt = (data/np.max(data)*255).astype(np.int)
                
                imgRGB_Mapped = np.stack([imgInt,imgInt,imgInt],axis=2)
                im = Image.fromarray((imgRGB_Mapped * 255).astype(np.uint8))
                
                data2 = im.tobytes("raw","RGB")
                qim = QImage(data2, im.size[0], im.size[1], QImage.Format_RGB888)
                rotate = QTransform()
                rotate.rotate(270)
                qimg = qim.transformed(rotate)
                pix = QPixmap.fromImage(qimg)
                self.setImage(pix)   
                
                
    
    def getImgWidth(self):
        if self.__imgorientation == 1:   #x-y
            if self.__pixeldims is not None:
                return self.__pixeldims[0]
            else:
                return 0
        elif self.__imgorientation == 2:  #x-z
            if self.__pixeldims is not None:
                return self.__pixeldims[0]
            else:
                return 0
        else:                          #y-z
            if self.__pixeldims is not None:
                return self.__pixeldims[1]
            else:
                return 0            
        
    def getImgHeight(self):
        if self.__imgorientation == 1:   #x-y
            if self.__pixeldims is not None:
                return self.__pixeldims[1]
            else:
                return 0
        elif self.__imgorientation == 2:  #x-z
            if self.__pixeldims is not None:
                return self.__pixeldims[2]
            else:
                return 0
        else:                          #y-z
            if self.__pixeldims is not None:
                return self.__pixeldims[2]
            else:
                return 0  
        
    def getSliceMin(self):
        return 0
    
    def getSliceMax(self):
        if self.__imgorientation == 1:   #x-y
            if self.__pixeldims is not None:
                return self.__pixeldims[2]-1
            else:
                return 0
        elif self.__imgorientation == 2:  #x-z
            if self.__pixeldims is not None:
                return self.__pixeldims[1]-1
            else:
                return 0
        else:                          #y-z
            if self.__pixeldims is not None:
                return self.__pixeldims[0]-1
            else:
                return 0
    
    def getSliceRange(self):
        if self.__imgorientation == 1:   #x-y
            if self.__pixeldims is not None:
                return self.__pixeldims[2]
            else:
                return 0
        elif self.__imgorientation == 2:  #x-z
            if self.__pixeldims is not None:
                return self.__pixeldims[1]
            else:
                return 0
        else:                          #y-z
            if self.__pixeldims is not None:
                return self.__pixeldims[0]
            else:
                return 0
            
    def getImageData(self):
        return self.__imageData
    
    
    def getSliceImageData(self):
        if self.__imgorientation == 1:   #x-y
            data = self.__imageData[:,:,self.__curSlice]               
        elif self.__imgorientation == 2:  #x-z
            data = self.__imageData[:,self.__curSlice,:]
        else:                          #y-z
            data = self.__imageData[self.__curSlice,:,:]
        
        return data
    
    def loadDicomSeries(self, folderName=""):  
        '''
        lstFilesDCM = []
            
        for dirName, subdirList, fileList in os.walk(folderName):
            for filename in fileList:
                if ".dcm" in filename.lower():
                    lstFilesDCM.append(os.path.join(dirName, filename))
    
        # Get ref file
        RefDs = dicom.read_file(lstFilesDCM[0])
        
        self.__pixeldims = [int(RefDs.Rows), int(RefDs.Columns), len(lstFilesDCM)]
        self.__pixelspacing = [(float)(RefDs.PixelSpacing[0]), (float)(RefDs.PixelSpacing[1]), (float)(RefDs.SliceThickness)]
        
        self.__imageData = np.zeros(self.__pixeldims, dtype=float)
        self.__fileName = folderName
    
        # It cannot read compressed dicom data
        for filenameDCM in lstFilesDCM:
            # read the file
            ds = dicom.read_file(filenameDCM)
            # store the raw image data
            self.__imageData[:, :, lstFilesDCM.index(filenameDCM)] = ds.pixel_array    
        '''
        reader = sitk.ImageSeriesReader()
        series_ids = reader.GetGDCMSeriesIDs(str(folderName))        
        assert len(series_ids) == 1, 'Assuming only one series per folder.'
        filenames = reader.GetGDCMSeriesFileNames(str(folderName), series_ids[0])
        reader.SetFileNames(filenames)        
        image = reader.Execute()
        
        self.__pixeldims = image.GetSize()
        self.__pixelspacing = image.GetSpacing()
        self.__imageData = sitk.GetArrayFromImage(image) #np.transpose(sitk.GetArrayFromImage(image), axes=[2,1,0])
        self.__winlevel = self.__imageData.min()
        self.__winwidth = self.__imageData.max()-self.__imageData.min()         
        self.__imgorientation = 1 # x-y
        self.__curSlice = self.__pixeldims[2]//2
        self.setSlice(self.__curSlice) 
        
        #self.resampleImage() works, but it takes time to get isotropic image
        
        self.__fileName = str(folderName)        
        
    def loadNIFTI(self, fileName=""):
        if len(fileName) and os.path.isfile(fileName):
            img = nib.load(fileName)
        
            self.__pixeldims = list(img.shape)
            self.__pixelspacing = list(img.header.get_zooms())
            self.__imageData = img.get_data()
            self.__winlevel = self.__imageData.min()
            self.__winwidth = self.__imageData.max()-self.__imageData.min()  
            self.__imgorientation = 1 # x-y   
            self.__curSlice = self.__pixeldims[2]//2
            self.setSlice(self.__curSlice)
            
            self.__fileName = fileName

    def loadFile(self, fileName="", orientation=1):
        if len(fileName) and os.path.isfile(fileName):
            ext = os.path.splitext(fileName)[-1]
            if("nii" in ext):
                img = nib.load(fileName) 
                
                self.__pixeldims = list(img.shape)
                self.__imageData = img.get_data()
                self.__imgorientation = orientation # x-y   
                self.__curSlice = self.__pixeldims[2]//2
                
                
                if self.__imgorientation == 1:   #x-y
                    data = self.imgProcessing(self.__imageData[:,:,self.__curSlice]) 
                    imgInt = (data/np.max(data)*255).astype(np.int)
                    self.__winlevel = self.__imageData.min()
                    self.__winwidth = self.__imageData.max()-self.__imageData.min()  
                elif self.__imgorientation == 2:  #x-z
                    data = self.imgProcessing(self.__imageData[:,self.__curSlice,:])  
                    imgInt = (data/np.max(data)*255).astype(np.int)
                    self.__winlevel = self.__imageData.min()
                    self.__winwidth = self.__imageData.max()-self.__imageData.min()  
                else:                          #y-z
                    data = self.imgProcessing(self.__imageData[self.__curSlice,:,:])    
                    imgInt = (data/np.max(data)*255).astype(np.int)
                    self.__winlevel = self.__imageData.min()
                    self.__winwidth = self.__imageData.max()-self.__imageData.min()
                    
                self.setSlice(self.__curSlice)
                
            elif("mat" in ext):
                #FIX THIS!!!!
                img = scipy.io.loadmat(fileName)['a6_CORONALCHEST_']
        
                self.__pixeldims = list(np.shape(img))
                self.__imageData = img
                self.__imgorientation = orientation # x-y   
                self.__curSlice = self.__pixeldims[2]//2
                
                
                if self.__imgorientation == 1:   #x-y
                    data = self.imgProcessing(self.__imageData[:,:,self.__curSlice]) 
                    imgInt = (data/np.max(data)*255).astype(np.int)
                    self.__winlevel = self.__imageData.min()
                    self.__winwidth = self.__imageData.max()-self.__imageData.min()  
                elif self.__imgorientation == 2:  #x-z
                    data = self.imgProcessing(self.__imageData[:,self.__curSlice,:])  
                    imgInt = (data/np.max(data)*255).astype(np.int)
                    self.__winlevel = self.__imageData.min()
                    self.__winwidth = self.__imageData.max()-self.__imageData.min()  
                else:                          #y-z
                    data = self.imgProcessing(self.__imageData[self.__curSlice,:,:])    
                    imgInt = (data/np.max(data)*255).astype(np.int)
                    self.__winlevel = self.__imageData.min()
                    self.__winwidth = self.__imageData.max()-self.__imageData.min() 
                
                self.setSlice(self.__curSlice)
                
            else:
                print("File type error -- please use an accepted file type")
            
            self.__fileName = fileName
            
            
    def loadCmap(self, img):
        self.__imageData = img

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        if not self.hasImage():
            return
        if len(self.zoomStack) and self.sceneRect().contains(self.zoomStack[-1]):
            self.fitInView(self.zoomStack[-1], Qt.KeepAspectRatio)  # Show zoomed rect (ignore aspect ratio).
        else:
            self.zoomStack = []  # Clear the zoom stack (in case we got here because of an invalid zoom).
            self.fitInView(self.sceneRect(), self.aspectRatioMode)  # Show entire image (use current aspect ratio mode).

    def resizeEvent(self, event):
        """ Maintain current zoom on resize.
        """
        self.updateViewer()

    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.RightButton:
            if self.canPan:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.leftMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.LeftButton:
            if self.canZoom:
                self.setDragMode(QGraphicsView.RubberBandDrag)
            self.rightMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        QGraphicsView.mouseReleaseEvent(self, event)
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.RightButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.leftMouseButtonReleased.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.LeftButton:
            if self.canZoom:
#                 viewBBox = self.zoomStack[-1] if len(self.zoomStack) else self.sceneRect()
                viewBBox = self.sceneRect()
                selectionBBox = self.scene.selectionArea().boundingRect().intersected(viewBBox)
                self.scene.setSelectionArea(QPainterPath())  # Clear current selection area.
                if selectionBBox.isValid() and (selectionBBox != viewBBox):
                    self.zoomStack.append(selectionBBox)
                    self.updateViewer()
            self.setDragMode(QGraphicsView.NoDrag)
            self.rightMouseButtonReleased.emit(scenePos.x(), scenePos.y())

    def mouseDoubleClickEvent(self, event):
        """ Show entire image.
        """
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.RightButton:
            self.leftMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.LeftButton:
            if self.canZoom:
                self.zoomStack = []  # Clear zoom stack.
                self.updateViewer()
            self.rightMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        QGraphicsView.mouseDoubleClickEvent(self, event)
        
    def mouseMoveEvent(self, event):
        scenePos = self.mapToScene(event.pos())
        
        # record the position for cross drawing
        self.__lineX.setLine(scenePos.x(),self.sceneRect().y(),scenePos.x(), self.sceneRect().y()+ self.sceneRect().height())      
        self.__lineY.setLine(self.sceneRect().x(),scenePos.y(),self.sceneRect().x()+ self.sceneRect().width(),scenePos.y())  
        
        self.scene.invalidate(self.scene.sceneRect())
        QGraphicsView.mouseMoveEvent(self, event)  # in PyQt5, update() doesn't trigger drawForeground()
        
    def drawForeground(self, painter, rect):
        if self.__crossshow == True:
            painter.save()
            pen = QPen()
            pen.setWidth(2)
            pen.setColor(QColor(255,0,0))
            painter.setPen(pen)
            painter.drawLine(self.__lineX)
            pen.setColor(QColor(0,255,0))
            painter.setPen(pen)        
            painter.drawLine(self.__lineY)
            painter.restore()
        QGraphicsView.drawForeground(self, painter, rect)          

