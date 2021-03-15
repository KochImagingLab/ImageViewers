#! /usr/bin/env python3
""" 
QtImageViewer.py: PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.

"""

import os.path
import os
import sys
import Segmenter

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
        
        else:  # 2D seed segmentation

            print('2D Segmentation')

            if self.__imgorientation == 1:
                seedy = self.getImgHeight()-1-row
                seedx = column
                thisSlicePlane = self.__imageDataOrig[:,:,self.getCurSlice()]
            elif self.__imgorientation == 2:
                seedy = self.getImgHeight()-1-row
                seedx = column
                thisSlicePlane = self.__imageDataOrig[:,self.getCurSlice(),:]
            elif self.__imgorientation == 3:
                seedy = self.getImgHeight()-1-row
                seedx = column
                thisSlicePlane = self.__imageDataOrig[self.getCurSlice(),:,:]
            else:
                print("ERROR: Invlaid plane")
                
            sitk.WriteImage(sitk.GetImageFromArray(thisSlicePlane),'origImg.nii')
            
            #sitk_image = sitk.GetImageFromArray(thisSlice)
        
            #self.__segInfo[
        
            print(row)
            print(column)
            print(seedx)
            print(seedy)
            print(thisSlicePlane.shape)
            print(thisSlicePlane[seedx,seedy])
            
            
            segBox = self.drawSegBox2D(thisSlicePlane,seedx,seedy,0)
            segSliceOut = self.segSliceBasedOnSeed(thisSlicePlane,seedx,seedy,0,thSet)
            
            sitk.WriteImage(sitk.GetImageFromArray(np.transpose(segSliceOut, axes=[1,0])),'fullSeg.nii')
            
            #thisSlicePlane = thisSlicePlane+32767*segSliceOut
            sliceVis = np.where(segSliceOut > 0,32766,thisSlicePlane)
            sliceVis2 = np.where(segBox > 0,32766,sliceVis)
            
            print(np.amax(thisSlicePlane))
           
            sitk.WriteImage(sitk.GetImageFromArray(np.transpose(sliceVis2, axes=[1,0])),'fullSegVis.nii')
            
            #print(thisSlicePlane[seedx,seedy])
            
            #thisSlicePlane = 0
            
            #self.__imageData[:,:,self.getCurSlice()] = thisSlicePlane
           
            self.__segInfo[0,self.getCurSlice()] = seedx
            self.__segInfo[1,self.getCurSlice()] = seedy
            self.__segInfo[2,self.getCurSlice()] = 0
            self.__segInfo[3,self.getCurSlice()] = thSet
           
            if self.__imgorientation == 1:
                self.__imageData[:,:,self.getCurSlice()] = sliceVis2
                self.__segData[:,:,self.getCurSlice()] = segSliceOut
                self.__segBox[:,:,self.getCurSlice()] = segBox
            elif self.__imgorientation == 2:
                self.__imageData[:,self.getCurSlice(),:] = sliceVis2
                self.__segData[:,self.getCurSlice(),:] = segSliceOut
                self.__segBox[:,self.getCurSlice(),:] = segBox
            elif self.__imgorientation == 3:
                self.__imageData[self.getCurSlice(),:,:] = sliceVis2
                self.__segData[self.getCurSlice(),:,:] = segSliceOut
                self.__segBox[self.getCurSlice(),:,:] = segBox
            else:
                print("ERROR: Invlaid plane")
           
            print('Data saved')
           
            #sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__imageData, axes=[2,1,0])),'fullSegVis3D.nii')
           
            #self.__imageData[:,:,self.getCurSlice] = np.transpose(sitk.GetArrayFromImage(resampled_sitk_image), axes=[1,0])
        
        self.setSlice(self.__curSlice)
    
    
    def drawSegBox2D(self,sliceIn,seedx,seedy,boneInd):
    
        # define 2D bounding box size
        boneBound = 50  # will need to tweak this for each bone -- I've only looked at scaphoid
        if(boneInd==0):
            boneBound = 50

        if(boneInd==1):
            boneBound = 50
    
        if(boneInd==2):
            boneBound = 80

        cSize = boneBound
        
        # identify the search bounding box
        x0 = int(np.round(seedx-cSize/2))
        x1 = int(np.round(seedx+cSize/2-1))
        y0 = int(np.round(seedy-cSize/2))
        y1 = int(np.round(seedy+cSize/2-1))

        # crop the image to the bounding box
        boxFill = np.zeros(sliceIn.shape)
        boxFill[x0:x1,y0:y1] = 1
        
        boxITK = sitk.GetImageFromArray(boxFill)
        edge = sitk.CannyEdgeDetection(boxITK, lowerThreshold=0, upperThreshold=0.2,
                                 variance=[1] * 3)
                                 
        boxSeg = sitk.GetArrayFromImage(edge)
        
        return boxSeg
        
    
    def segSliceBasedOnSeed(self,sliceIn,seedx,seedy,boneInd,thSet):
    
        print("Into Segmenter")
    
        # define 2D bounding box size
        boneBound = 50  # will need to tweak this for each bone -- I've only looked at scaphoid
        if(boneInd==0):
            boneBound = 50

        if(boneInd==1):
            boneBound = 50
    
        if(boneInd==2):
            boneBound = 80

        newINP = sliceIn

        cSize = boneBound
        
        print(seedx)
        print(seedy)
        
        # identify the search bounding box
        x0 = int(np.round(seedx-cSize/2))
        x1 = int(np.round(seedx+cSize/2-1))
        y0 = int(np.round(seedy-cSize/2))
        y1 = int(np.round(seedy+cSize/2-1))

        print(x0)
        print(y0)

        # reset the seeed indices within the bounding box
        newSS = np.zeros([2,2])   # x and y are reversed in ITK arrays --
        newSS[0][0] = seedx - x0
        newSS[0][1] = seedy - y0
        newSS[1][0] = seedx - x0
        newSS[1][1] = seedy - y0

        newSeeds = list(map(tuple,np.array(newSS, dtype='int').tolist()))

        # crop the image to the bounding box
        cropSection = newINP[x0:x1,y0:y1]
        
        print("Histogram Analysis")
        # compute histogram of signal within bounding box
        histogram, bin_edges = np.histogram(cropSection, bins=50, range=(0, np.amax(cropSection)))
        
        # identify the peaks of the histogram
        peak_indices = signal.find_peaks_cwt(histogram, np.arange(1,10))
        
        # extract the counts of the peaks
        peakVals = histogram[peak_indices]
        
        # this switch is important
        # if we have more than 2 peaks, we find the maximum peak beyond the "low signal"
        # peak, and then use it to bisect the "low signal" and "high signal" peaks.
        # this is used as the threshold.
        # if we don't find two peaks, we set it to the middle bin of the histogram
        # (where it seems that most of the thresholds seem to reside)
        
        if(len(peakVals) > 2):
            
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

        print(thresh)
        
        print("Segmenting")
        

        cropSectionITK = sitk.GetImageFromArray(cropSection)
        
        print(newSeeds)

        
        seg = sitk.ConnectedThreshold(cropSectionITK, seedList=newSeeds, lower=0, upper=thresh)


        print("Growing done")
        segFilled = sitk.VotingBinaryHoleFilling(image1=seg,
                                                          radius=[2]*3,
                                                          majorityThreshold=1,
                                                          backgroundValue=0,
                                                          foregroundValue=1)
        print("Holes filled")
        vectorRadius=(1,1,1)
        kernel=sitk.sitkBall
        segCleaned = sitk.BinaryMorphologicalOpening(segFilled,vectorRadius,kernel)
        segNP = sitk.GetArrayFromImage(segCleaned)

        sitk.WriteImage(segCleaned,'segImg.nii')
        sitk.WriteImage(cropSectionITK,'cropImg.nii')

                                                          
        print("Edges cleaned")

        # re-pad to full slice
        # crop the image to the bounding box
        fullSegNP = np.zeros(newINP.shape)
        fullSegNP[x0:x1,y0:y1] = segNP

        print("Returning")


        return fullSegNP
    
    
    def writeOutputFiles(self,outFile):
    
        niiFile = '%s_seg.nii' % outFile
        pStr = 'Outputting segmentation to file %s' % niiFile
        print(pStr)
        
        sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__segData, axes=[2,1,0])),niiFile)
       
        niiFile = '%s_segBox.nii' % outFile
        pStr = 'Outputting segmentation to file %s' % niiFile
        print(pStr)
       
        sitk.WriteImage(sitk.GetImageFromArray(np.transpose(self.__segBox, axes=[2,1,0])),niiFile)
    
    
        infoFile = '%s_segInfo.npy' % outFile
        pStr = 'Outputting info to file %s' % infoFile
        print(pStr)
        np.save(infoFile,self.__segInfo)
     
     
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
    
#    def getCrosshair(self):
#        return self.__crosshair
       
    def get_qimage(self,image:np.ndarray):
#         assert (np.max(image) <= 256)
        image8 = image.astype(np.uint8, order='C', casting='unsafe')
        height, width = image8.shape
        bytesPerLine = width
        image = QImage(image8.data, width, height, bytesPerLine, QImage.Format_Indexed8)
        return image
 
    def setSlice(self, slice):
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
        self.__segInfo = np.zeros((4,inShape[2]))
        
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
            self.__imageDataOrig = img.get_data().copy()
            self.__segData = np.zeros(self.__imageData.shape)
            self.__segBox = np.zeros(self.__imageData.shape)
            inShape = self.__imageData.shape
            self.__segInfo = np.zeros((4,inShape[2]))
            
            self.__winlevel = self.__imageData.min()
            self.__winwidth = self.__imageData.max()-self.__imageData.min()  
            self.__imgorientation = 1 # x-y   
            self.__curSlice = self.__pixeldims[2]//2
            self.setSlice(self.__curSlice)
            
            self.__fileName = fileName

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

