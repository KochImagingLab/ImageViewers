#! /usr/bin/env python3
""" 
QtImageViewer.py: PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.

"""

import os.path
import os
import sys
import Segmenter
import inspect

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import nibabel as nib
import SimpleITK as sitk
import PyQt5

import scipy.ndimage
import scipy.io as sio
from scipy import signal

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QT_VERSION_STR, QLineF, QRegExp
from PyQt5.QtGui import QImage, QPixmap, QPainterPath, QPainter, QPen, QColor, QIntValidator, QTransform, QBrush
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QGroupBox,\
                            QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QLineEdit,QPushButton,\
                            QGraphicsLineItem, QScrollBar, QCheckBox, QComboBox, QAbstractItemView, QLabel
from PyQt5.QtWidgets import QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

import matplotlib
import matplotlib.cm as cm
import matplotlib.pyplot as plt
import matplotlib.cbook as cbook
from matplotlib.path import Path
from matplotlib.patches import PathPatch
matplotlib.use('TkAgg')


__author__ = ""
__version__ = ""


#class CrosshairWindow(FigureCanvasQTAgg):
#
#    def __init__(self, parent=None, width=5, height=4, dpi=100):
#        self.fig = Figure(figsize=(width, height), dpi=dpi)
#        self.axes1 = self.fig.add_subplot(211)
#        self.axes1.set_title("Vertical Profile")
#        self.axes2 = self.fig.add_subplot(212)
#        self.axes2.set_title("Horizontal Profile")
#        self.fig.subplots_adjust(hspace=0.8)
#        super(CrosshairWindow, self).__init__(self.fig)
#

#class ThruPlaneWindow(FigureCanvasQTAgg):
#
#    def __init__(self, parent=None, width=5, height=4, dpi=100):
#        self.fig2 = Figure(figsize=(width, height), dpi=dpi)
#        self.plt1 = self.fig2.add_subplot(221)
#        self.plt2 = self.fig2.add_subplot(222)
#        self.plt3 = self.fig2.add_subplot(212)
#
#        self.fig2.subplots_adjust(hspace=0.8, wspace=0.5)
#
#
#        super(ThruPlaneWindow, self).__init__(self.fig2)



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
        
        
#         scene = QGraphicsScene()
#         view = QGraphicsView(scene)
#         view.show()
        
        
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
        #self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        #self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Stack of QRectF zoom boxes in scene coordinates.
        self.zoomStack = []
        
        # -------------------
        self.__fileName = None
        self.__imageData = None
        self.__segData = None
        self.__segBox = None
        self.__segInfo = None
        self.__pixeldims = None
        self.__pixelspacing = None
        self.__imgorientation = 1
        self.__curSlice = 0
        self.__bboxIP = 0.2
        self.__bboxSL = 0.95
        
#        # -------------------
#        self.__crossshow = False
#        self.__lineX = QLineF()
#        self.__lineY = QLineF()
        
#        # -------------------
#        self.__crosshair = 0
#        self.__thruPlane = 0
#        self.__vert = 0
#        self.__horiz = 0
        self.__flipX = False
        self.__flipY = False
        self.__rotateAngle = 270
        
        # -------------------
        self.__winlevel = 0
        self.__winwidth = 256
        
        self.__ROITemplate = None

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
        #self.setSliceOrientation(self.__imgorientation)
        self.updateViewer()
        

    def setOrientation(self,orient):
        
        self.__imgorientation = orient
        
        
    

#    def buildCrosshairPopup(self):
#        self.ch = CrosshairWindow(self, width=5, height=4, dpi=100)
#
#        if self.__imgorientation == 1:
#            horizArr = self.__imageData[:,0,self.getCurSlice()]
#            vertArr = self.__imageData[0,:,self.getCurSlice()]
#        elif self.__imgorientation == 2:
#            horizArr = self.__imageData[:,self.getCurSlice(),0]
#            vertArr = self.__imageData[0,self.getCurSlice(),:]
#        elif self.__imgorientation == 3:
#            horizArr = self.__imageData[self.getCurSlice(),:,0]
#            vertArr = self.__imageData[self.getCurSlice(),0,:]
#        else:
#            print("ERROR: Invlaid plane")
#
#        self.ch.axes1.plot(vertArr)
#        self.ch.axes2.plot(horizArr)
#        self.ch.show()
#
#        self.display_VertLine(self.getVertVal())
#        self.display_HorizLine(self.getHorizVal())
#
            
#    def clearCrosshairPopup(self):
#        self.ch.close()
#        self.__crosshair = 0
#        self.scene.removeItem(self.HLine)
#        self.scene.removeItem(self.VLine)
#        self.setHorizVal(0)
#        self.setVertVal(0)
#        if(self.__thruPlane == 2):
#            self.__thruPlane = 0
#            self.tp.close()
#
#    def setCrosshair(self, value):
#        if self.__imageData is not None:
#            self.__crosshair = value
#            if(value == 2):
#                self.buildCrosshairPopup()
#            else:
#                self.clearCrosshairPopup()
#        else:
#            return 0
#
#
#    def buildThruPlanePopup(self):
#        self.tp = ThruPlaneWindow(self, width=5, height=4, dpi=100)
#
#        if self.__imgorientation == 1:
#            data1 = np.rot90(self.__imageData[:,self.getHorizVal(),:])
#            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:])
#            data3 = self.__imageData[self.getVertVal(),self.getHorizVal(),:]
#        elif self.__imgorientation == 2:
#            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
#            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:])
#            data3 = self.__imageData[self.getVertVal(),:,self.getHorizVal()]
#        elif self.__imgorientation == 3:
#            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
#            data2 = np.rot90(self.__imageData[:,self.getVertVal(),:])
#            data3 = self.__imageData[:,self.getVertVal(),self.getHorizVal()]
#
#
#        self.tp.plt1.imshow(data1, aspect='auto')
#        self.tp.plt2.imshow(data2, aspect='auto')
#        self.tp.plt3.plot(data3)
#
#        self.tp.plt3.set_title("Through-Plane Profile")
#        self.tp.plt3.set_xlabel("Slice Number")
#        self.tp.plt3.set_xlim([0, int(self.getSliceMax())])
#
#        self.tp.show()
#
#        self.display_VertLine(self.getVertVal())
#        self.display_HorizLine(self.getHorizVal())
#
#
#    def updateThroughPlane(self):
#        if self.__imgorientation == 1:
#            data1 = np.rot90(self.__imageData[:,self.getHorizVal(),:])
#            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:])
#            data3 = self.__imageData[self.getVertVal(),self.getImgHeight()-1-self.getHorizVal(),:]
#        elif self.__imgorientation == 2:
#            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
#            data2 = np.rot90(self.__imageData[self.getVertVal(),:,:])
#            data3 = self.__imageData[self.getVertVal(),:,self.getImgHeight()-1-self.getHorizVal()]
#        elif self.__imgorientation == 3:
#            data1 = np.rot90(self.__imageData[:,:,self.getHorizVal()])
#            data2 = np.rot90(self.__imageData[:,self.getVertVal(),:])
#            data3 = self.__imageData[:,self.getVertVal(),self.getImgHeight()-1-self.getHorizVal()]
#
#
#        self.tp.plt1.clear()
#        self.tp.plt2.clear()
#        self.tp.plt3.clear()
#
#        self.tp.plt1.imshow(data1, aspect='auto')
#        self.tp.plt2.imshow(data2, aspect='auto')
#        self.tp.plt3.plot(data3)
#
#        self.tp.plt3.set_title("Through-Plane Profile")
#        self.tp.plt3.set_xlabel("Slice Number")
#        self.tp.plt3.set_xlim([0, int(self.getSliceMax())])
#
#        self.tp.draw()
#
#
#    def clearThruPlanePopup(self):
#        self.tp.close()
#
#
#    def setThruPlane(self, value):
#        self.__thruPlane = value
#        if(value == 2):
#            self.buildThruPlanePopup()
#        else:
#            self.clearThruPlanePopup()
#
#    def updateVerticalProfile(self, value):
#        self.setVertVal(value)
#
#        if self.__imgorientation == 1:
#            vertArr = self.__imageData[value,:,self.getCurSlice()]
#        elif self.__imgorientation == 2:
#            vertArr = self.__imageData[value,self.getCurSlice(),:]
#        elif self.__imgorientation == 3:
#            vertArr = self.__imageData[self.getCurSlice(),value,:]
#        else:
#            print("ERROR: Invlaid plane")
#
#
#        self.ch.axes1.clear()
#        self.ch.axes1.set_title("Vertical Profile")
#        self.ch.axes1.plot(vertArr)
#        self.ch.draw()
#
#        if(self.__thruPlane == 2):
#            self.updateThroughPlane()
#
#        self.display_VertLine(value)
#
#    def updateHorizontalProfile(self, value):
#        self.setHorizVal(value)
#
#
#        if self.__imgorientation == 1:
#            horizArr = self.__imageData[:,self.getImgHeight()-1-value,self.getCurSlice()]
#        elif self.__imgorientation == 2:
#            horizArr = self.__imageData[:,self.getCurSlice(),self.getImgHeight()-1-value]
#        elif self.__imgorientation == 3:
#            horizArr = self.__imageData[self.getCurSlice(),:,self.getImgHeight()-1-value]
#        else:
#            print("ERROR: Invlaid plane")
#
#        self.ch.axes2.clear()
#        self.ch.axes2.set_title("Horizontal Profile")
#        self.ch.axes2.plot(horizArr)
#        self.ch.draw()
#
#        if(self.__thruPlane == 2):
#            self.updateThroughPlane()
#        self.display_HorizLine(value)
#
#    def display_VertLine(self, value):
#        try:
#            self.scene.removeItem(self.VLine)
#        except:
#            pass
#        self.VLine = self.scene.addLine(value, 0, value, self.getImgHeight(), QPen(Qt.red))
#
#
#    def display_HorizLine(self, value):
#        try:
#            self.scene.removeItem(self.HLine)
#        except:
#            pass
#        self.HLine = self.scene.addLine(0, value, self.getImgWidth(), value, QPen(Qt.green))
#

#    def getHorizVal(self):
#        return self.__horiz
#
#    def getVertVal(self):
#        return self.__vert
#
#    def setHorizVal(self, value):
#        self.__horiz = value
#
#    def setVertVal(self, value):
#        self.__vert = value

    
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
        
    
    def segmentImageCallback(self,row,column,thSet,procThree):
        
    
        if procThree == 2:   # 3D seed segmentation
        
            print('ThreeD Segmentation')
        
            #BS needs to be recalculated based on orientation
            if(self.__imgorientation == 1):
                seedx = self.getImgHeight()-1-row
                seedy = self.getCurSlice()
                seedz = column
            elif(self.__imgorientation == 2):
                print("Segmentation for this orientation has not been tested!")
                seedx = self.getCurSlice()
                seedy = column 
                seedz = self.getImgHeight()-1-row 
            else: #0 or 3
#                 seedx = column
#                 seedy = self.getImgHeight()-1-row
                seedx = self.getImgHeight()-1-row #column
                seedy = column #self.getImgHeight()-1-row
                seedz = self.getCurSlice()
            
            print('Shape and Seeds')
            print('   {}'.format(self.__imageData.shape))
            print('   {},{},{}'.format(seedx,seedy,seedz))
            
            #sitk.WriteImage(sitk.GetImageFromArray(thisSlicePlane),'origImg.nii')
            
            #sitk_image = sitk.GetImageFromArray(thisSlice)
        
            #self.__segInfo[
        
            #print(row)
            #print(column)
            #print(seedx)
            #print(seedy)
            #print(thisSlicePlane.shape)
            #print(thisSlicePlane[seedx,seedy])

            thisVol = self.__imageDataOrig
            
            
            segBox = self.drawSegBox3D(thisVol,seedx,seedy,seedz)
            segVolOut = self.segVolBasedOnSeed(thisVol,seedx,seedy,seedz,thSet)
            
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(segSliceOut, axes=[1,0])),'fullSeg.nii')
            
            #thisSlicePlane = thisSlicePlane+32767*segSliceOut
            volVis = np.where(segVolOut > 0,32766,thisVol)
            volVis2 = np.where(segBox > 0,32766,volVis)
            
            #print(np.amax(thisSlicePlane))
           
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(sliceVis2, axes=[1,0])),'fullSegVis.nii')
            
            #print(thisSlicePlane[seedx,seedy])
            
            #thisSlicePlane = 0
            
            #self.__imageData[:,:,self.getCurSlice()] = thisSlicePlane

            self.__segInfo = self.__segInfo*0.0
            self.__segInfo[0,self.getCurSlice()] = seedx
            self.__segInfo[1,self.getCurSlice()] = seedy
            self.__segInfo[2,self.getCurSlice()] = self.__bboxIP
            self.__segInfo[3,self.getCurSlice()] = self.__bboxSL
            self.__segInfo[4,self.getCurSlice()] = thSet

            self.__imageData = volVis2
            self.__segData = segVolOut
            self.__segBox = segBox

            print('Data saved')
        
        else:  # 2D seed segmentation

            #print('2D Segmentation')

          
            seedy = self.getImgHeight()-1-row
            seedx = column
            
            if(self.__imgorientation == 1):
                thisSlicePlane = self.__imageDataOrig[:,self.getCurSlice(),:]
            elif(self.__imgorientation == 2):
                thisSlicePlane = self.__imageDataOrig[:,:,self.getCurSlice()]
            else:
                thisSlicePlane = self.__imageDataOrig[self.getCurSlice(),:,:]
                
            #sitk.WriteImage(sitk.GetImageFromArray(thisSlicePlane),'origImg.nii')
            
            #sitk_image = sitk.GetImageFromArray(thisSlice)
        
            #self.__segInfo[
        
            #print(row)
            #print(column)
            #print(seedx)
            #print(seedy)
            #print(thisSlicePlane.shape)
            #print(thisSlicePlane[seedx,seedy])
            
            
            segBox = self.drawSegBox2D(thisSlicePlane,seedx,seedy)
            segSliceOut = self.segSliceBasedOnSeed(thisSlicePlane,seedx,seedy,thSet)
            
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(segSliceOut, axes=[1,0])),'fullSeg.nii')
            
            #thisSlicePlane = thisSlicePlane+32767*segSliceOut
            sliceVis = np.where(segSliceOut > 0,32766,thisSlicePlane)
            sliceVis2 = np.where(segBox > 0,32766,sliceVis)
            
            #print(np.amax(thisSlicePlane))
           
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(sliceVis2, axes=[1,0])),'fullSegVis.nii')
            
            #print(thisSlicePlane[seedx,seedy])
            
            #thisSlicePlane = 0
            
            #self.__imageData[:,:,self.getCurSlice()] = thisSlicePlane
           
            self.__segInfo[0,self.getCurSlice()] = seedx
            self.__segInfo[1,self.getCurSlice()] = seedy
            self.__segInfo[2,self.getCurSlice()] = self.__bboxIP
            self.__segInfo[3,self.getCurSlice()] = self.__bboxSL
            self.__segInfo[4,self.getCurSlice()] = thSet
           
            if(self.__imgorientation == 1):
                self.__imageData[:,self.getCurSlice(),:] = sliceVis2
                self.__segData[:,self.getCurSlice(),:] = segSliceOut
                self.__segBox[:,self.getCurSlice(),:] = segBox
            elif(self.__imgorientation == 2):
                
                self.__imageData[:,:,self.getCurSlice()] = sliceVis2
                self.__segData[:,:,self.getCurSlice()] = segSliceOut
                self.__segBox[:,:,self.getCurSlice()] = segBox
            else:
    
                self.__imageData[self.getCurSlice(),:,:] = sliceVis2
                self.__segData[self.getCurSlice(),:,:] = segSliceOut
                self.__segBox[self.getCurSlice(),:,:] = segBox

           
            print('Data saved')
           
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__imageData, axes=[2,1,0])),'fullSegVis3D.nii')
           
            #self.__imageData[:,:,self.getCurSlice] = np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[1,0])
        
        self.setSlice(self.__curSlice)
    
    
    def drawSegBox2D(self,sliceIn,seedx,seedy):
    
        # define 2D bounding box size
        #boneBound = 50  # will need to tweak this for each bone -- I've only looked at scaphoid
        #if(boneInd==0):
        #    boneBound = 50

        #if(boneInd==1):
        #    boneBound = 50
    
        #if(boneInd==2):
        #    boneBound = 80


        sliceShape = sliceIn.shape
        
        #only adding to get it to stop crashing
#         if(self.__imgorientation == 1):
        cSizeX = np.round(self.__bboxIP*sliceShape[0])
        cSizeY = np.round(self.__bboxIP*sliceShape[1])
#         elif(self.__imgorientation == 2):
#             
#             cSizeX = np.round(self.__bboxIP*sliceShape[2])
#             cSizeY = np.round(self.__bboxIP*sliceShape[0])
#         else:
#             
#             cSizeX = np.round(self.__bboxIP*sliceShape[0])
#             cSizeY = np.round(self.__bboxIP*sliceShape[1])
        print("{}: 2d x,y:  {},{}".format(inspect.stack()[0][3],cSizeX,cSizeY))
        
        #print(cSizeX)
        #print(self.__bboxIP)
        
        # identify the search bounding box
        x0 = int(np.round(seedx-cSizeX/2))
        x1 = int(np.round(seedx+cSizeX/2-1))
        y0 = int(np.round(seedy-cSizeY/2))
        y1 = int(np.round(seedy+cSizeY/2-1))

        # crop the image to the bounding box
        boxFill = np.zeros(sliceIn.shape)
        boxFill[x0:x1+1,y0:y1+1] = 1
        
        boxITK = sitk.GetImageFromArray(boxFill)
        edge = sitk.CannyEdgeDetection(boxITK, lowerThreshold=0, upperThreshold=0.2,
                                 variance=[1] * 3)
                                 
        boxSeg = sitk.GetArrayFromImage(edge)
        
        return boxSeg
    
    def drawSegBox3D(self,volIn,seedx,seedy,seedz):

        volShape = volIn.shape
        
        if(self.__imgorientation == 1):
            cSizeX = np.round(self.__bboxIP*volShape[0])
            cSizeY = np.round(self.__bboxSL*volShape[1])
            cSizeZ = np.round(self.__bboxIP*volShape[2])
        elif(self.__imgorientation == 2):
            cSizeX = np.round(self.__bboxIP*volShape[2])
            cSizeY = np.round(self.__bboxIP*volShape[0])
            cSizeZ = np.round(self.__bboxSL*volShape[1])
        else:
            cSizeX = np.round(self.__bboxIP*volShape[1])
            cSizeY = np.round(self.__bboxIP*volShape[2])
            cSizeZ = np.round(self.__bboxSL*volShape[0])

        #print(cSizeX)
        #print(self.__bboxIP)
        
        # identify the search bounding box
        x0 = int(np.round(seedx-cSizeX/2))
        x1 = int(np.round(seedx+cSizeX/2-1))
        y0 = int(np.round(seedy-cSizeY/2))
        y1 = int(np.round(seedy+cSizeY/2-1))
        z0 = int(np.round(seedz-cSizeZ/2))
        z1 = int(np.round(seedz+cSizeZ/2-1))
        
        if(x0 < 0):
            x0 = 0

        if(y0 < 0):
            y0 = 0

        if(z0 < 0):
            z0 = 0

        if(x1 > volShape[2]-1):
            x1 = volShape[2]-1

        if(y1 > volShape[1]-1):
            y1 = volShape[1]-1

        if(z1 > volShape[0]-1):
            z1 = volShape[0]-1
        

        # crop the image to the bounding box
        boxFill = np.zeros(volIn.shape)

        boxFill[z0:z1+1,y0:y1+1,x0:x1+1] = 1
        
        boxITK = sitk.GetImageFromArray(boxFill)
        edge = sitk.CannyEdgeDetection(boxITK, lowerThreshold=0, upperThreshold=0.2,
                                 variance=[1] * 3)
                                 
        boxSeg = sitk.GetArrayFromImage(edge)
        
        #TODO: clear the center of the top and bottom as viewed
        #edgebox = boxSeg[z0-1,:,:] #change to appropriate axis based on orientation
        #boxITK = sitk.GetImageFromArray(edgebox)
        #edge = sitk.CannyEdgeDetection(boxITK, lowerThreshold=0, upperThreshold=0.2,
        #                         variance=[1] * 3)
        #edgebox = sitk.GetArrayFromImage(edge)
        #boxSeg[z0-1,:,:] = edgebox
        #nevermind, there's a way easier way
        if(self.__imgorientation == 1):
            boxSeg[:,y0,:] = boxSeg[:,y0+1,:]
            boxSeg[:,y1,:] = boxSeg[:,y1-1,:]
        elif(self.__imgorientation == 2):
            #like everywhere else, orientation 2 still needs to be straightened out
            boxSeg[:,:,x0] = boxSeg[:,:,x0+1]
            boxSeg[:,:,x1]=boxSeg[:,:,x1-1]
        else:
            boxSeg[z0,:,:] = boxSeg[z0+1,:,:]
            boxSeg[z1,:,:]=boxSeg[z1-1,:,:]
        
        return boxSeg
        
    
    def segVolBasedOnSeed(self,volIn,seedx,seedy,seedz,thSet):
    
        #print("Into Segmenter")
    
        # define 2D bounding box size
#        boneBound = 50  # will need to tweak this for each bone -- I've only looked at scaphoid
#        if(boneInd==0):
#            boneBound = 50
#
#        if(boneInd==1):
#            boneBound = 50
#
#        if(boneInd==2):
#            boneBound = 80

        newINP = volIn

#        cSize = boneBound
#
#        #print(seedx)
#        #print(seedy)
#
#        # identify the search bounding box
#        x0 = int(np.round(seedx-cSize/2))
#        x1 = int(np.round(seedx+cSize/2-1))
#        y0 = int(np.round(seedy-cSize/2))
#        y1 = int(np.round(seedy+cSize/2-1))

        volShape = volIn.shape
        
        print("{}: volShape:  {}".format(inspect.stack()[0][3],volShape))
        print("{}: imgorient: {}".format(inspect.stack()[0][3],self.__imgorientation))
        print("{}: seeds:     {},{},{}".format(inspect.stack()[0][3],seedx,seedy,seedz))
        
        if(self.__imgorientation == 1):
            cSizeX = np.round(self.__bboxIP*volShape[0])
            cSizeY = np.round(self.__bboxSL*volShape[1])
            cSizeZ = np.round(self.__bboxIP*volShape[2])
        elif(self.__imgorientation == 2):
            cSizeX = np.round(self.__bboxIP*volShape[1])
            cSizeY = np.round(self.__bboxSL*volShape[2])
            cSizeZ = np.round(self.__bboxIP*volShape[0])
        else:
            cSizeX = np.round(self.__bboxIP*volShape[1])
            cSizeY = np.round(self.__bboxIP*volShape[2])
            cSizeZ = np.round(self.__bboxSL*volShape[0])
           
        # identify the search bounding box
        x0 = int(np.round(seedx-cSizeX/2))
        x1 = int(np.round(seedx+cSizeX/2-1))
        y0 = int(np.round(seedy-cSizeY/2))
        y1 = int(np.round(seedy+cSizeY/2-1))
        z0 = int(np.round(seedz-cSizeZ/2))
        z1 = int(np.round(seedz+cSizeZ/2-1))
        
        if(x0 < 0):
            x0 = 0

        if(y0 < 0):
            y0 = 0

        if(z0 < 0):
            z0 = 0

        if(x1 > volShape[2]-1):
            x1 = volShape[2]-1
 
        if(y1 > volShape[1]-1):
            y1 = volShape[1]-1
 
        if(z1 > volShape[0]-1):
            z1 = volShape[0]-1
            
        # reset the seeed indices within the bounding box
        newSS = np.zeros([2,3])   # x and y are reversed in ITK arrays --
        newSS[0][0] = seedx - x0
        newSS[0][1] = seedy - y0
        newSS[0][2] = seedz - z0
       
        newSS[1][0] = seedx - x0
        newSS[1][1] = seedy - y0
        newSS[1][2] = seedz - z0

        newSeeds = list(map(tuple,np.array(newSS, dtype='int').tolist()))

        # crop the image to the bounding box
        cropSection = newINP[z0:z1+1,y0:y1+1,x0:x1+1]
        
        print("{}: bboxSL:  {}".format(inspect.stack()[0][3],self.__bboxSL))
        
        print("{}: x vals:  {},{}".format(inspect.stack()[0][3],x0,x1))
        print("{}: y vals:  {},{}".format(inspect.stack()[0][3],y0,y1))
        print("{}: z vals:  {},{}".format(inspect.stack()[0][3],z0,z1))
              
        cropSectionITK = sitk.GetImageFromArray(cropSection)
        sitk.WriteImage(cropSectionITK,'cropImg3D.nii')
        
        #print("Histogram Analysis")
        # compute histogram of signal within bounding box
        histogram, bin_edges = np.histogram(cropSection, bins=50, range=(0, np.amax(cropSection)))
        
        # identify the peaks of the histogram
        #peak_indices = signal.find_peaks_cwt(histogram, np.arange(1,10))
        peak_indices,_ = signal.find_peaks( histogram) 
        
        # extract the counts of the peaks
        peakVals = histogram[peak_indices]
        
        #print(histogram)
        #print(peak_indices)
        #print(peakVals)
        
        # this switch is important
        # if we have more than 2 peaks, we find the maximum peak beyond the "low signal"
        # peak, and then use it to bisect the "low signal" and "high signal" peaks.
        # this is used as the threshold.
        # if we don't find two peaks, we set it to the middle bin of the histogram
        # (where it seems that most of the thresholds seem to reside)
        
        if(len(peakVals) > 6):
            #if we have lots of peaks, drop the first few items to make sure we're clear of the low signal
            drop = int(.25*len(peakVals))
            
            testVals = peakVals[range(drop,len(peakVals))]
            index = np.argmax(testVals)
            
            thresh = thSet*(bin_edges[peak_indices[index+drop]]-bin_edges[peak_indices[0]])
        
        elif(len(peakVals) > 2):
            
            testVals = peakVals[range(1,len(peakVals))]
            index = np.argmax(testVals)
            
            #print(index)
            
            thresh = thSet*(bin_edges[peak_indices[index+1]]-bin_edges[peak_indices[0]])
        
        else:
            
            if(len(peakVals)==2):
            
                thresh = thSet*(bin_edges[peak_indices[1]]-bin_edges[peak_indices[0]])

            else:
                print('WARNING: PEAKS NOT IDENTIFIED, THRESHOLD IS A ROUGH GUESS')
                #thresh = bin_edges[np.round(len(bin_edges)/2)]
                thresh = thSet*bin_edges[26]
                
        print("{}: threshold:  {}".format(inspect.stack()[0][3],thresh))
        
        #print("Segmenting")
        

 
        print("{}: crop section shape:  {}".format(inspect.stack()[0][3],cropSection.shape))
        print("{}:          new seeds:  {}".format(inspect.stack()[0][3],newSeeds))

        
        seg = sitk.ConnectedThreshold(cropSectionITK, seedList=newSeeds, lower=0, upper=thresh)


        #print("Growing done")
        segFilled = sitk.VotingBinaryHoleFilling(image1=seg,
                                                          radius=[2]*3,
                                                          majorityThreshold=1,
                                                          backgroundValue=0,
                                                          foregroundValue=1)
        #print("Holes filled")
        vectorRadius=(1,1,1)
        kernel=sitk.sitkBall
        segCleaned = sitk.BinaryMorphologicalOpening(segFilled,vectorRadius,kernel)
        segNP = sitk.GetArrayFromImage(segCleaned)

        #sitk.WriteImage(segCleaned,'segImg.nii')
        #sitk.WriteImage(cropSectionITK,'cropImg.nii')

                                                          
        #print("Edges cleaned")

        # re-pad to full slices
        # crop the image to the bounding box
        fullSegNP = np.zeros(newINP.shape)
        fullSegNP[z0:z1+1,y0:y1+1,x0:x1+1] = segNP

        #print("Returning")
        
        return fullSegNP
    
    ##### KMK working --- need to build 3D seg function now
    
    def segSliceBasedOnSeed(self,sliceIn,seedx,seedy,thSet):
    
        #print("Into Segmenter")
    
        # define 2D bounding box size
#        boneBound = 50  # will need to tweak this for each bone -- I've only looked at scaphoid
#        if(boneInd==0):
#            boneBound = 50
#
#        if(boneInd==1):
#            boneBound = 50
#
#        if(boneInd==2):
#            boneBound = 80

        newINP = sliceIn

#        cSize = boneBound
#
#        #print(seedx)
#        #print(seedy)
#
#        # identify the search bounding box
#        x0 = int(np.round(seedx-cSize/2))
#        x1 = int(np.round(seedx+cSize/2-1))
#        y0 = int(np.round(seedy-cSize/2))
#        y1 = int(np.round(seedy+cSize/2-1))

        sliceShape = sliceIn.shape
        
        cSizeX = np.round(self.__bboxIP*sliceShape[0])
        cSizeY = np.round(self.__bboxIP*sliceShape[1])
        
        #print(cSizeX)
        #print(self.__bboxIP)
        
        # identify the search bounding box
        x0 = int(np.round(seedx-cSizeX/2))
        x1 = int(np.round(seedx+cSizeX/2-1))
        y0 = int(np.round(seedy-cSizeY/2))
        y1 = int(np.round(seedy+cSizeY/2-1))

        #print(x0)
        #print(y0)

        # reset the seeed indices within the bounding box
        newSS = np.zeros([2,2])   # x and y are reversed in ITK arrays --
        newSS[0][0] = seedx - x0
        newSS[0][1] = seedy - y0
        newSS[1][0] = seedx - x0
        newSS[1][1] = seedy - y0

        newSeeds = list(map(tuple,np.array(newSS, dtype='int').tolist()))

        # crop the image to the bounding box
        cropSection = newINP[x0:x1,y0:y1]
        
        #print("Histogram Analysis")
        # compute histogram of signal within bounding box
        histogram, bin_edges = np.histogram(cropSection, bins=50, range=(0, np.amax(cropSection)))
        
        # identify the peaks of the histogram
        #peak_indices = signal.find_peaks_cwt(histogram, np.arange(1,10))
        #okay, here's our problem, sometimes we have two peaks in the low signal, so, two thoughts
        peak_indices,_ = signal.find_peaks(histogram)
        #peak_indices3 = signal.find_peaks_cwt(histogram, np.arange(3,10))
        
        # extract the counts of the peaks
        peakVals = histogram[peak_indices]
        
        
        # this switch is important
        # if we have more than 2 peaks, we find the maximum peak beyond the "low signal"
        # peak, and then use it to bisect the "low signal" and "high signal" peaks.
        # this is used as the threshold.
        # if we don't find two peaks, we set it to the middle bin of the histogram
        # (where it seems that most of the thresholds seem to reside)
        
        if(len(peakVals) > 6):
            #if we have lots of peaks, drop the first few items to make sure we're clear of the low signal
            drop = int(.25*len(peakVals))
            
            testVals = peakVals[range(drop,len(peakVals))]
            index = np.argmax(testVals)
            
            thresh = thSet*(bin_edges[peak_indices[index+drop]]-bin_edges[peak_indices[0]])
        
        elif(len(peakVals) > 2):
            
            testVals = peakVals[range(1,len(peakVals))]
            index = np.argmax(testVals)
            
            thresh = thSet*(bin_edges[peak_indices[index+1]]-bin_edges[peak_indices[0]])
        
        
        else:
            
            if(len(peakVals)==2):
            
                thresh = thSet*(bin_edges[peak_indices[1]]-bin_edges[peak_indices[0]])

            else:
                print('WARNING: PEAKS NOT IDENTIFIED, THRESHOLD IS A ROUGH GUESS')
                #thresh = bin_edges[np.round(len(bin_edges)/2)]
                thresh = thSet*bin_edges[26]

        print(thresh)
        
        print("{}: threshold:  {}".format(inspect.stack()[0][3],thresh))
        
        #print("Segmenting")
        

        cropSectionITK = sitk.GetImageFromArray(cropSection)
        
        #print(newSeeds)

        seg = sitk.ConnectedThreshold(cropSectionITK, seedList=newSeeds, lower=0, upper=thresh)


        #print("Growing done")
        segFilled = sitk.VotingBinaryHoleFilling(image1=seg,
                                                          radius=[2]*3,
                                                          majorityThreshold=1,
                                                          backgroundValue=0,
                                                          foregroundValue=1)
        #print("Holes filled")
        vectorRadius=(1,1,1)
        kernel=sitk.sitkBall
        segCleaned = sitk.BinaryMorphologicalOpening(segFilled,vectorRadius,kernel)
        segNP = sitk.GetArrayFromImage(segCleaned)

        #sitk.WriteImage(segCleaned,'segImg.nii')
        #sitk.WriteImage(cropSectionITK,'cropImg.nii')

                                                          
        #print("Edges cleaned")

        # re-pad to full slice
        # crop the image to the bounding box
        fullSegNP = np.zeros(newINP.shape)
        fullSegNP[x0:x1,y0:y1] = segNP

        #print("Returning")


        return fullSegNP
    
    
    def writeOutputFiles(self,outFile):
        
        if(outFile.endswith("nii") or outFile.endswith( "nii.gz") ):
            niiFile = outFile 
        else:
            niiFile = '%s_seg.nii' % outFile
        pStr = 'Outputting segmentation to file %s' % niiFile
        print(pStr)
        
        if(self.__imgorientation == 1):
            sitk_image = sitk.GetImageFromArray(np.transpose(self.__segData, axes=[2,1,0]))
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__segData, axes=[2,1,0])),niiFile)
        elif(self.__imgorientation == 2):
            print("This one is wrong, needs to be fixed if you're using it.")
            sitk_image = sitk.GetImageFromArray(np.transpose(self.__segData, axes=[1,0,2]))
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__segData, axes=[2,1,0])),niiFile)
        else:
            sitk_image = sitk.GetImageFromArray(np.transpose(self.__segData, axes=[0,1,2]))
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__segData, axes=[0,1,2])),niiFile)
#         sitk_image.SetSpacing([float(self.__pixelspacing[0]), \
#                                 float(self.__pixelspacing[1]), \
#                                 float(self.__pixelspacing[2])])
        if(self.__ROITemplate != None):
            print("Copying header.")
            sitk_image.CopyInformation(self.__ROITemplate)
        else:
            print("Did not copy header.")
        sitk.WriteImage(sitk_image,niiFile)
           
        niiFile = '%s_segBox.nii' % outFile
        pStr = 'Outputting segmentation to file %s' % niiFile
        print(pStr)
       
        sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__segBox, axes=[2,1,0])),niiFile)
        
    
        infoFile = '%s_segInfo.npy' % outFile
        pStr = 'Outputting info to file %s' % infoFile
        print(pStr)
        np.save(infoFile,self.__segInfo)
     
    def resampleImage(self,ipFact,slFact):
    
        pStr ='Resampling image volume to higher resolution by factors %f and %f ' % (ipFact,slFact)
        print(pStr)
    
        print("{}: input last slice sum:  {}".format(inspect.stack()[0][3],np.sum(self.__imageData[:,:,-1])))
        print("{}: input 2last slice sum:  {}".format(inspect.stack()[0][3],np.sum(self.__imageData[:,:,-2])))
        print("{}: input 3last slice sum:  {}".format(inspect.stack()[0][3],np.sum(self.__imageData[:,:,-3])))
        
        sitk_image = sitk.GetImageFromArray(self.__imageData)
        sitk_image.SetSpacing([float(self.__pixelspacing[2]), \
                                float(self.__pixelspacing[1]), \
                                float(self.__pixelspacing[0])])
        print("{}: spacing:  {}".format(inspect.stack()[0][3],sitk_image.GetSpacing()))
        num_dim = sitk_image.GetDimension()
        orig_pixelid = sitk_image.GetPixelIDValue()
        orig_origin = sitk_image.GetOrigin()
        orig_direction = sitk_image.GetDirection()
        orig_spacing = sitk_image.GetSpacing()
        orig_size = np.array(sitk_image.GetSize(), dtype=np.int)
    
        print(orig_spacing)
        new_spacing = [orig_spacing[0]/ipFact,orig_spacing[1]/slFact, orig_spacing[2]/ipFact]
 #       new_spacing[1] =
 #       new_spacing[2] =
        
        sitk_interpolator = sitk.sitkLinear
    
        new_size = orig_size*(np.array(orig_spacing)/np.array(new_spacing))
        new_size = np.ceil(new_size).astype(np.int) #  Image dimensions are in integers
        new_size = [int(s) for s in new_size] #  SimpleITK expects lists, not ndarrays
    
        resample_filter = sitk.ResampleImageFilter()
    
        #update for sitk 2.0.2 - not yet tested
        resample_filter.SetSize(new_size)
        resample_filter.SetTransform(sitk.Transform())
        resample_filter.SetInterpolator(sitk_interpolator)
        resample_filter.SetOutputOrigin(orig_origin)
        resample_filter.SetOutputSpacing(new_spacing)
        resample_filter.SetOutputOrigin(orig_direction)
        resample_filter.SetOutputPixelType(orig_pixelid)
        resampled_sitk_image = resample_filter.Execute(sitk_image)
        
        
        tmp=np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[2,1,0])
        print("{}: lstSlice:  {}".format(inspect.stack()[0][3],np.sum(tmp[-1,:,:])))
        print("{}: 2lstSlice:  {}".format(inspect.stack()[0][3],np.sum(tmp[-2,:,:])))
        print("{}: 3lstSlice:  {}".format(inspect.stack()[0][3],np.sum(tmp[-3,:,:])))
    
#         resampled_sitk_image = resample_filter.Execute(sitk_image,
#                                                        new_size,
#                                                        sitk.Transform(),
#                                                        sitk_interpolator,
#                                                        orig_origin,
#                                                        new_spacing,
#                                                        orig_direction,
#                                                        0,
#                                                        orig_pixelid)
                                                       
        self.__imageData = np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[2,1,0])
        self.__pixeldims = self.__imageData.shape
        self.__pixelspacing = new_spacing
        self.__winlevel = self.__imageData.min()
        self.__winwidth = self.__imageData.max()-self.__imageData.min()
#        self.__imgorientation = 1 # x-y
#        self.__curSlice = self.__pixeldims[2]//2
#        self.setSlice(self.__curSlice)
                                                       
       
    
        #outputImage = np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[2,1,0])
        
#    def resampleImage(self, spacing=None,fill_value=0):
#
#        sitk_image = sitk.GetImageFromArray(self.__imageData)
#        sitk_image.SetSpacing([float(self.__pixelspacing[2]), \
#                               float(self.__pixelspacing[1]), \
#                               float(self.__pixelspacing[0])])
#
#        num_dim = sitk_image.GetDimension()
#        orig_pixelid = sitk_image.GetPixelIDValue()
#        orig_origin = sitk_image.GetOrigin()
#        orig_direction = sitk_image.GetDirection()
#        orig_spacing = sitk_image.GetSpacing()
#        orig_size = np.array(sitk_image.GetSize(), dtype=np.int)
#
#        if spacing is None:
#            min_spacing = min(orig_spacing)
#            new_spacing = [min_spacing]*num_dim
#        else:
#            new_spacing = [float(s) for s in spacing]
#
#        sitk_interpolator = sitk.sitkLinear
#
#        new_size = orig_size*(np.array(orig_spacing)/np.array(new_spacing))
#        new_size = np.ceil(new_size).astype(np.int) #  Image dimensions are in integers
#        new_size = [int(s) for s in new_size] #  SimpleITK expects lists, not ndarrays
#
#        resample_filter = sitk.ResampleImageFilter()
#
#        resampled_sitk_image = resample_filter.Execute(sitk_image,
#                                                       new_size,
#                                                       sitk.Transform(),
#                                                       sitk_interpolator,
#                                                       orig_origin,
#                                                       new_spacing,
#                                                       orig_direction,
#                                                       fill_value,
#                                                       orig_pixelid)
#
#        self.__imageData = np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[2,1,0])
#        self.__pixeldims = self.__imageData.shape
#        self.__pixelspacing = [new_spacing,new_spacing,new_spacing]
#        self.__winlevel = self.__imageData.min()
#        self.__winwidth = self.__imageData.max()-self.__imageData.min()
#        self.__imgorientation = 1 # x-y
#        self.__curSlice = self.__pixeldims[2]//2
#        self.setSlice(self.__curSlice)



    def resampleImageSpec(self,myImg,ipFact,slFact):
        
        pStr ='Resampling ROI volume to higher resolution by factors %f and %f ' % (ipFact,slFact)
        print(pStr)
        print("{}: input last slice sum:  {}".format(inspect.stack()[0][3],np.sum(myImg[:,:,-1])))
        print("{}: input 2last slice sum:  {}".format(inspect.stack()[0][3],np.sum(myImg[:,:,-2])))
        print("{}: input 3last slice sum:  {}".format(inspect.stack()[0][3],np.sum(myImg[:,:,-3])))
        sitk_image = sitk.GetImageFromArray(myImg)
        #should be corrected when loading the initial nifti
        sitk_image.SetSpacing([float(self.__pixelspacing[0]), \
                                float(self.__pixelspacing[1]), \
                                float(self.__pixelspacing[2])])
        
        print("{}: spacing:  {}".format(inspect.stack()[0][3],sitk_image.GetSpacing()))
        
        num_dim = sitk_image.GetDimension()
        print("{}: num dims:  {}".format(inspect.stack()[0][3],num_dim))
        orig_pixelid = sitk_image.GetPixelIDValue()
        orig_origin = sitk_image.GetOrigin()
        orig_direction = sitk_image.GetDirection()
        orig_spacing = sitk_image.GetSpacing()
        print("{}: spacing:  {}".format(inspect.stack()[0][3],orig_spacing))
        orig_size = np.array(sitk_image.GetSize(), dtype=np.int)
        print("{}: orig_size:  {}".format(inspect.stack()[0][3],orig_size))
        
        #print("{}: lstSlice:  {}".format(inspect.stack()[0][3],np.sum(myImg[-1,:,:])))
    
        new_spacing = [orig_spacing[0]/ipFact,orig_spacing[1]/slFact, orig_spacing[2]/ipFact]
        
        #sitk_interpolator = sitk.sitkLinear
        sitk_interpolator = sitk.sitkNearestNeighbor
    
        new_size = orig_size*(np.array(orig_spacing)/np.array(new_spacing))
        new_size = np.ceil(new_size).astype(np.int) #  Image dimensions are in integers
        new_size = [int(s) for s in new_size] #  SimpleITK expects lists, not ndarrays
        print("{}: new_size:  {}".format(inspect.stack()[0][3],new_size))
    
        resample_filter = sitk.ResampleImageFilter()
    
        #update for sitk 2.0.2 - not yet tested
        resample_filter.SetSize(new_size)
        resample_filter.SetTransform(sitk.Transform())
        resample_filter.SetInterpolator(sitk_interpolator)
        resample_filter.SetOutputOrigin(orig_origin)
        resample_filter.SetOutputSpacing(new_spacing)
        resample_filter.SetOutputOrigin(orig_direction)
        resample_filter.SetOutputPixelType(orig_pixelid)
        resampled_sitk_image = resample_filter.Execute(sitk_image)
        
        tmp=np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[2,1,0])
        print("{}: lstSlice:  {}".format(inspect.stack()[0][3],np.sum(tmp[-1,:,:])))
        print("{}: 2lstSlice:  {}".format(inspect.stack()[0][3],np.sum(tmp[-2,:,:])))
        print("{}: 3lstSlice:  {}".format(inspect.stack()[0][3],np.sum(tmp[-3,:,:])))
                                                       
        return(np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[2,1,0]))
        
#    def setCrossShow(self, value):
#        if value == 0:
#            self.__crossshow = False
#        else:
#            self.__crossshow = True
#
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
            return [self.__imageData.min(), self.__imageData.max()]  
    
    def getWinWidthRange(self):
        if self.__imageData is None:
            return [0,1]
        else:
            return [0, self.__imageData.max()-self.__imageData.min()]  
            
    def setSliceOrientation(self, orientation=9999):
        print("or:{}    curSli:{}    shape:{}    or:{}".format(orientation, self.__curSlice, self.__imageData.shape, self.__imgorientation))
        if orientation == 9999:
            orientation = self.__imgorientation
        if orientation == 1:
            self.__imgorientation = 1
            #self.setSliceOrientationToXY()
            self.setSliceOrientationToXZ()
        elif orientation == 2:   
            self.__imgorientation = 2
            #self.setSliceOrientationToXZ()
            self.setSliceOrientationToXY()
        else:
            self.__imgorientation = 3
            self.setSliceOrientationToYZ()
    
    def setSliceOrientationToXY(self):
        self.__imgorientation = 2
        if (self.__imageData is not None):
            self.__curSlice = int(np.round(self.__pixeldims[2]/2))
            self.setSlice(self.__curSlice)
            
    
    def setSliceOrientationToXZ(self):
        self.__imgorientation = 1
        if (self.__imageData is not None):
            self.__curSlice = int(np.round(self.__pixeldims[1]/2))
            #print('INTO XZ')
            #print(self.__curSlice)
            self.setSlice(self.__curSlice) 
    
    def setSliceOrientationToYZ(self):
        self.__imgorientation = 3
        if (self.__imageData is not None):
            self.__curSlice = int(np.round(self.__pixeldims[0]//2))
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
    
#    def getCrosshair(self):
#        return self.__crosshair
       
    def get_qimage(self,image:np.ndarray):
#         assert (np.max(image) <= 256)
        image8 = image.astype(np.uint8, order='C', casting='unsafe')
        height, width = image8.shape
        bytesPerLine = width
        image = QImage(image8.data, width, height, bytesPerLine, QImage.Format_Indexed8)
        return image
 
    def setbbox(self, ipValue,slValue):
        self.__bboxIP = ipValue
        self.__bboxSL = slValue
 
    def setSlice(self, slice):
        if (self.__imageData is not None) and (slice>=self.getSliceMin() and slice<=self.getSliceMax()):
            self.__curSlice = slice
            #print(self.__imgorientation)
            #print(slice)
            if self.__imgorientation == 1:   #x-y
#                 localData = self.__imageData[:,:,slice]
                #print("test: {}   {}".format(self.__imageData.shape, slice))
                #data = self.imgProcessing(self.__imageData[:,:,slice])  
                data = self.imgProcessing(self.__imageData[:,slice,:])  
                qimage = self.get_qimage(data)
#                 qimage = qimage.mirrored(self.__flipX, self.__flipY)
                rotate = QTransform()
                rotate.rotate(self.__rotateAngle)
                qimg = qimage.transformed(rotate)
                self.setImage(qimg)                
            elif self.__imgorientation == 2:  #x-z
                #data = self.imgProcessing(self.__imageData[:,slice,:]) 
                data = self.imgProcessing(self.__imageData[:,:,slice])              
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
    
    #NOTE: I'm fairly certain one of the x,y combos is flipped in these two functions
    #probably orientation 2 should be 1 and 0 instead of 0 and 1
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
                return self.__pixeldims[2]
            else:
                return 0  
        
    def getSliceMin(self):
        return 0
    
    def getSliceMax(self):
        #print('into get slicemax')
        #print(self.getCurSlice())
        if self.__imgorientation == 1:   #x-y
            if self.__pixeldims is not None:
                return self.__pixeldims[1]-1
            else:
                return 0
        elif self.__imgorientation == 2:  #x-z
            if self.__pixeldims is not None:
                return self.__pixeldims[2]-1
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
                return self.__pixeldims[0]
            else:
                return 0
            
    def get_bboxIP(self):
        return self.__bboxIP
    
    def get_bboxSL(self):
        return self.__bboxSL
    
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
        self.__segData = np.zeros(self.__imageData.shape)
        self.__segBox = np.zeros(self.__imageData.shape)
        inShape = self.__imageData.shape
        self.__segInfo = np.zeros((5,inShape[2]))
        
        self.__winlevel = self.__imageData.min()
        self.__winwidth = self.__imageData.max()-self.__imageData.min()         
        self.__imgorientation = 1 # x-y
        self.__curSlice = self.__pixeldims[2]//2
        self.setSlice(self.__curSlice) 
        
        #self.resampleImage() works, but it takes time to get isotropic image
        
        self.__fileName = str(folderName)        
        
    def loadNIFTI(self, fileName="",ipFact=1.0,slFact=1.0):
        if len(fileName) and os.path.isfile(fileName):
            img = nib.load(fileName)
        

            self.__pixeldims = list(img.shape)
            self.__pixelspacing = list(img.header.get_zooms())
            self.__imageData = img.get_data()
            
            print("input size: {}".format(self.__imageData.shape))
            self.resampleImage(ipFact,slFact)
            print("resam size: {}".format(self.__imageData.shape))

            self.__imageDataOrig = self.__imageData.copy()

            self.__segData = np.zeros(self.__imageData.shape)
            self.__segBox = np.zeros(self.__imageData.shape)
            inShape = self.__imageData.shape
            self.__segInfo = np.zeros((5,inShape[2]))
            
            self.__winlevel = self.__imageData.min()
            self.__winwidth = self.__imageData.max()-self.__imageData.min()  
            #print("{}      {}".format(self.__imageData.shape, np.argmin(self.__imageData.shape)))
            self.__imgorientation = np.argmin(self.__imageData.shape) # x-y
            
               
            self.__curSlice = int(self.__pixeldims[self.__imgorientation]//2)
            self.setSlice(self.__curSlice)
            
            self.__fileName = fileName
            
    def loadNIFTIseg(self, fileName="",ipFact=1.0,slFact=1.0):
        if len(fileName) and os.path.isfile(fileName) and self.hasImage():
            img = nib.load(fileName)
            self.__ROITemplate = sitk.ReadImage(fileName)
            self.__segData = self.resampleImageSpec(img.get_data(),ipFact,slFact)
            
            thisVol = self.__imageDataOrig
            segVolOut = self.__segData
            print("{}: volShape:  {}".format(inspect.stack()[0][3],thisVol.shape))
            print("{}: segShape:  {}".format(inspect.stack()[0][3],segVolOut.shape))
            
            volVis = np.where(segVolOut > 0,32766,thisVol)
            self.__imageData = volVis
            self.__segData = segVolOut
            
            self.setSlice(self.__curSlice)
            

    def loadImageFromFile(self, fileName=""):
        """ Load an image from file.
        Without any arguments, loadImageFromFile() will popup a file dialog to choose the image file.
        With a __fileName argument, loadImageFromFile(__fileName) will attempt to load the specified image file directly.
        """
        fileName, dummy = QFileDialog.getOpenFileName(self, "Open image file.")
        if len(fileName) and os.path.isfile(fileName):
            image = QImage(fileName)
            self.setImage(image)

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        if not self.hasImage():
            return
        if len(self.zoomStack) and self.sceneRect().contains(self.zoomStack[-1]):
            self.fitInView(self.zoomStack[-1], Qt.IgnoreAspectRatio)  # Show zoomed rect (ignore aspect ratio).
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
        if event.button() == Qt.LeftButton:
            if self.canPan:
                self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.leftMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.RightButton:
            if self.canZoom:
                self.setDragMode(QGraphicsView.RubberBandDrag)
            self.rightMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        QGraphicsView.mouseReleaseEvent(self, event)
        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.LeftButton:
            self.setDragMode(QGraphicsView.NoDrag)
            self.leftMouseButtonReleased.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.RightButton:
            if self.canZoom:
                viewBBox = self.zoomStack[-1] if len(self.zoomStack) else self.sceneRect()
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
        if event.button() == Qt.LeftButton:
            self.leftMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.RightButton:
            if self.canZoom:
                self.zoomStack = []  # Clear zoom stack.
                self.updateViewer()
            self.rightMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        QGraphicsView.mouseDoubleClickEvent(self, event)
        
    def mouseMoveEvent(self, event):
        scenePos = self.mapToScene(event.pos())
        
        # record the position for cross drawing
#        self.__lineX.setLine(scenePos.x(),self.sceneRect().y(),scenePos.x(), self.sceneRect().y()+ self.sceneRect().height())
#        self.__lineY.setLine(self.sceneRect().x(),scenePos.y(),self.sceneRect().x()+ self.sceneRect().width(),scenePos.y())
#
        self.scene.invalidate(self.scene.sceneRect())
        QGraphicsView.mouseMoveEvent(self, event)  # in PyQt5, update() doesn't trigger drawForeground()
        
    def drawForeground(self, painter, rect):
#        if self.__crossshow == True:
#            painter.save()
#            pen = QPen()
#            pen.setWidth(2)
#            pen.setColor(QColor(255,0,0))
#            painter.setPen(pen)
#            painter.drawLine(self.__lineX)
#            pen.setColor(QColor(0,255,0))
#            painter.setPen(pen)
#            painter.drawLine(self.__lineY)
#            painter.restore()
        QGraphicsView.drawForeground(self, painter, rect)          

