#! /usr/bin/env python3
""" 
QtImageViewer.py: PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.

v1.0 started updating to remove global variables
    Added in range bars for transparency and saturation

"""

import os.path
import os
import sys 
import argparse

import numpy as np
import nibabel as nib
import SimpleITK as sitk
import setup3D
import PyQt5

from PIL import ImageQt
from PIL import Image, ImageDraw

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QT_VERSION_STR, QLineF, QRegExp, QObject, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainterPath, QPainter, QPen, QColor, QIntValidator, QTransform
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QGroupBox,\
                            QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QLineEdit,QPushButton,\
                            QGraphicsLineItem, QScrollBar, QSlider, QCheckBox, QComboBox, QAbstractItemView, QLabel
from PyQt5.QtWidgets import QApplication


from rangeSlider import RangeSlider
#------------------------------------------------------------
# Event handling
#------------------------------------------------------------

        
def parseArgs():
    #parse all of the passed in arguments
    global args
    parser = argparse.ArgumentParser(description='Input parameters for where to copy database records.')
    parser.add_argument('-l', '--left', help='Path to nifti file for left image', default='') 
    parser.add_argument('-r', '--right', help='Path to nifti file for right image', default='') 
    
    args = parser.parse_args()
    
    return


def btn1Click():         
    global viewer1
    global winwidthScrollbar
    global winlevelScrollbar
    global winwidthText
    global winlevelText  
    global horscrollbar
    global verscrollbar
    global openFileText1
    global slicescrollbar
    global slicesTextbox
    global window
    global wwMin
    global wwMax
    global wlMin
    global wlMax
    global wwValue 
    global wlValue 
     
    fileName, dummy = QFileDialog.getOpenFileName(window, "Open image file.")
    if len(fileName) and os.path.isfile(fileName): 
        viewer1.loadNIFTI(fileName)
    else:
        return
                
    slicescrollbar.setMinimum(viewer1.getSliceMin())
    slicescrollbar.setMaximum(viewer1.getSliceMax())
    slicescrollbar.setValue(viewer1.getCurSlice())
    slicesTextbox.setText(str(viewer1.getCurSlice()))        
    
    wwMin = viewer1.getWinWidthRange()[0]
    wwMax = viewer1.getWinWidthRange()[1]
    wlMin = viewer1.getWinLevelRange()[0]
    wlMax = viewer1.getWinLevelRange()[1]

    wwValue = viewer1.getWindowWidth()
    wlValue = viewer1.getWindowLevel()        


    winwidthScrollbar.setValue(round(wwValue,4)+1) 
    winlevelScrollbar.setValue(round(wlMin,4)) 
    
    winwidthText.setText(str(round(wwValue,4)+1))
    winlevelText.setText(str(round(wlMin,4)))  
      
    viewer1.setWindowWidth(round(wwValue,4)+1)
    viewer1.setWindowLevel(wlMin)  
    
    
    horscrollbar.setMinimum(1)
    horscrollbar.setMaximum(int(viewer1.getImgHeight()))
    horscrollbar.setValue(viewer1.getHorizVal())
    horscrollbar.setPageStep(1)
    
    verscrollbar.setMinimum(1)
    verscrollbar.setMaximum(int(viewer1.getImgWidth()))
    verscrollbar.setValue(viewer1.getVertVal())
    verscrollbar.setPageStep(1)
    
      
    
    openFileText1.setText(fileName)
def enableCrosshair():
    global viewer1 
    global viewer2
    global horscrollbar
    global verscrollbar
    global crosshairsBox1
    global vlayout
    global chGroupBox
    global layout
    global thruplaneBox

    viewer1.setVertVal(viewer1.getImgWidth() // 2)
    viewer1.setHorizVal(viewer1.getImgHeight() // 2)
    viewer2.setVertVal(viewer1.getImgWidth() // 2)
    viewer2.setHorizVal(viewer1.getImgHeight() // 2)
    
    state = viewer1.setCrosshair(crosshairsBox1.checkState(), viewer2.getImageData())
    
    viewer2.display_VertLine(viewer2.getVertVal())
    viewer2.display_HorizLine(viewer2.getHorizVal())
    
    if(state != 0):
        if(crosshairsBox1.checkState() == 2):
            verscrollbar.setValue(viewer1.getVertVal())
            horscrollbar.setValue(viewer1.getHorizVal())
            vlayout.addWidget(chGroupBox)
        else:
            layout.removeWidget(chGroupBox)
            chGroupBox.setParent(None)
            thruplaneBox.setCheckState(0)
            viewer2.clearCrosshairs()
        
        
def enableThroughPlane():
    global viewer1
    global viewer2
    global thruplaneBox
    
    viewer1.setThruPlane(thruplaneBox.checkState(), viewer2.getImageData())
        
    
def handleLeftClick(x, y):
    global viewer1
    
    row = int(y)
    column = int(x)
    
    if( 0 <= row < viewer1.getImgHeight() and 0 <= column < viewer1.getImgWidth()):
        horizScrollChange(row)
        vertScrollChange(column)
        
def slicescrollbarChange(viewer, textbox, value, transparency, saturation):
    
    viewer.setSlice(value)
    colormap([viewer], transparency, saturation)
    textbox.setText(str(value))    
        
def slicetextEditChange(viewer, scrollbar, value, transparency, saturation):
    
    if int(value)<0:
        value = 0
    elif int(value)>viewer.getSliceMax():
        value = viewer.getSliceMax()
        
    viewer.setSlice(int(value))
    colormap([viewer], transparency, saturation)
    slicescrollbar.setValue(int(value))   
    
def wlscrollchange(viewerList, value,winlevelText,transparency, saturation):
    wlValue = float(value)
    for viewer in viewerList:
        viewer.setWindowLevel(wlValue)
        winlevelText.setText(str(round(wlValue,4)))
    
def wwscrollchange(viewerList, value,winwidthText,transparency, saturation):
    wwValue = float(value)      
    for viewer in viewerList: 
        viewer.setWindowWidth(wwValue)
        winwidthText.setText(str(round(wwValue,4)))
    
def wltextchange(viewerList, value,winlevelText,transparency, saturation):
    try:
        wlValue = float(value)
    except:
        wlValue = float(0)
        
    for viewer in viewerList:
        viewer.setWindowLevel(wlValue)
        winlevelText.setText(str(round(wlValue,4)))

def wwtextchange(viewerList, value,winwidthText,transparency, saturation):
    try:
        wwValue = float(value)
    except:
        wwValue = float(0)
        
    for viewer in viewerList:
        viewer.setWindowWidth(wwValue)
        winwidthText.setText(str(round(wwValue,4))) 
    
def ortChange(viewer, slicescroll, slicetext, verscroll, vertext, horscroll, hortext, crosshair, value):
    
    viewer.setSliceOrientation(value+1)
    
    if (viewer._pixmapHandle is not None): 
        slicescroll.setMaximum(viewer.getSliceMax())
        slicescroll.setValue(viewer.getCurSlice())
        slicetext.setText(str(viewer.getCurSlice()))   
        
        verscroll.setMaximum(int(viewer.getImgWidth()))
        
        viewer.setVertVal(viewer.getImgWidth() // 2)
        viewer.setHorizVal(viewer.getImgHeight() // 2)
        
        vertVal = viewer.getVertVal()
        horzVal = viewer.getHorizVal()
        
        vertext.setText(str(vertVal))
        verscroll.setValue(int(vertVal)) 
        if(crosshair.checkState() == 2):
            viewer.updateVerticalProfile(int(vertVal))
            
        horscroll.setMaximum(int(viewer.getImgHeight()))
        hortext.setText(str(horzVal))
        horscroll.setValue(int(horzVal)) 
        if(crosshair.checkState() == 2):
            viewer.updateHorizontalProfile(int(horzVal))

        
        
def horizScrollChange(value):
    global viewer1
    global viewer2
    global horscrollbar
    global horTextbox
    global crosshairsBox1
    
    if(crosshairsBox1.checkState() == 2):
        viewer1.updateHorizontalProfile(int(value)-1, viewer2.getImageData())
        viewer2.display_HorizLine(int(value)-1)
        
        
    horTextbox.setText(str(value))
    horscrollbar.setValue(int(value))  
    
def horizTextChange():
    global viewer1
    global viewer2
    global horscrollbar
    global horTextbox
    global crosshairsBox1
    
    value = horTextbox.text()
    if(crosshairsBox1.checkState() == 2):
        viewer1.updateHorizontalProfile(int(value)-1, viewer2.getImageData())
        viewer2.display_HorizLine(int(value)-1)

    horTextbox.setText(str(value))
    horscrollbar.setValue(int(value))   
    
def vertScrollChange(value):
    global viewer1
    global viewer2
    global verscrollbar
    global verTextbox
    global crosshairsBox1
    
    if(crosshairsBox1.checkState() == 2):
        viewer1.updateVerticalProfile(int(value)-1, viewer2.getImageData())
        viewer2.display_VertLine(int(value)-1)

    verTextbox.setText(str(value))
    verscrollbar.setValue(int(value))  
    
def vertTextChange():
    global viewer1
    global viewer2
    global verscrollbar
    global verTextbox
    global crosshairsBox1
    
    value = verTextbox.text()
    if(crosshairsBox1.checkState() == 2):
        viewer1.updateVerticalProfile(int(value)-1, viewer2.getImageData())
        viewer2.display_VertLine(int(value)-1)
        
    verTextbox.setText(str(value))
    verscrollbar.setValue(int(value))  
    
def colormap(viewerList, transparency, saturation):
    
    satLow, satHigh = saturation.value()
    tranLow, tranHigh = saturation.value()
     
    cmapRGB = np.array([245,66,66]) #A pretty nearly red color
     
    #Calculate number of points in the colormap
    if(tranLow > tranHigh):
        tranHigh = tranLow
         
    cmapPoints = int(tranHigh) - int(tranLow)
     
    #Calculate the number of points in the low ramp
    loRampPts = satLow-tranLow
     
    #Calculate the number of points in the high ramp
    hiRampPts = tranHigh-satHigh
 
    #Build the colormap
    cmapArray = np.zeros((cmapPoints,3))
    for cmapIdx in range(cmapPoints):
        #Compute the gray scale value to which this point corresponds
        gsValue = cmapIdx+tranLow
         
        #Easy part first--if saturated, put the pure color in
        if ((gsValue>satLow)and(gsValue<satHigh)):
            cmapArray[cmapIdx,:] = cmapRGB
             
        #Lower ramp up to saturation
        elif (gsValue <= satLow):
            #Cmpute transparency
            thisAlpha = np.float(cmapIdx) / np.float(loRampPts+0.0001)
            #Compute weights of gray versus color
            tmpGS = (1-thisAlpha)*gsValue
            tmpRGB = (thisAlpha)*cmapRGB
            #Make the colormap to be the weighted average 
            #(division by 1 implicit)
            for idx in range(3):
                cmapArray[cmapIdx,idx] = int(tmpGS)+tmpRGB[idx]
 
        #Upper ramp from saturation
        elif (gsValue >= satHigh):
            #Compute inverse transparency
            thisAlpha = np.float(gsValue-satHigh) / hiRampPts
            #Compute weights of gray versus color
            tmpGS = (thisAlpha)*gsValue
            tmpRGB = (1-thisAlpha)*cmapRGB
            #Make the colormap to be the weighted average 
            #(division by 1 implicit)
            for idx in range(3):
                cmapArray[cmapIdx,idx] = int(tmpGS)+tmpRGB[idx]
                     
                     
        #Go through the image, when the gray scale is in the range to switch, 
        # insert the colormap
        
    for viewer in viewerList:
        thisImg = viewer.getSliceImageData()
        imgInt = (thisImg/np.max(thisImg)*255).astype(np.int)
         
        imgRGB_Mapped = np.stack([imgInt,imgInt,imgInt],axis=2)
         
        for row in range(imgRGB_Mapped.shape[0]):
            for col in range(imgRGB_Mapped.shape[1]):
                thisValue = imgRGB_Mapped[row,col,0]
                if ((thisValue>tranLow)and(thisValue<tranHigh)):
                    cmapIdx = np.int(thisValue-tranLow)
                    imgRGB_Mapped[row,col,::] = cmapArray[cmapIdx,::]
                     
    
        im = Image.fromarray((imgRGB_Mapped * 255).astype(np.uint8))
        data = im.tobytes("raw","RGB")
        qim = QImage(data, im.size[0], im.size[1], QImage.Format_RGB888)
        rotate = QTransform()
        rotate.rotate(270)
        qimg = qim.transformed(rotate)
        pix = QPixmap.fromImage(qimg)
        viewer.setImage(pix)  
        
        
def colormapIncrement(viewerList, transparency, saturation, increment, location, slider):
    #increment: -1=increment down, 1=increment up
    #location: "high"=increment top value, "low"=increment low value
    #slider: "transparency"=increment transparency slider, "saturation"=increment saturation slider
    
    satLow, satHigh = saturation.value()
    tranLow, tranHigh = transparency.value()

    if(slider == "transparency"):
        if(location == 'high'):
            tranHigh=tranHigh+increment
            transparency.setValue(tranLow,tranHigh)
        elif(location == 'low'):
            tranLow=tranLow+increment
            transparency.setValue(tranLow,tranHigh)
        else:
            pass

    if(slider == "saturation"):
        if(location == 'high' ):
            satHigh=satHigh+increment
            saturation.setValue(satLow,satHigh)
        elif(location == 'low'):
            satLow=satLow+increment
            saturation.setValue(satLow,satHigh)
        else:
            pass
    
    
    cmapRGB = np.array([245,66,66]) #A pretty nearly red color
     
    #Calculate number of points in the colormap
    if(tranLow > tranHigh):
        tranHigh = tranLow
         
    cmapPoints = int(tranHigh) - int(tranLow)
     
    #Calculate the number of points in the low ramp
    loRampPts = satLow-tranLow
     
    #Calculate the number of points in the high ramp
    hiRampPts = tranHigh-satHigh
 
    #Build the colormap
    cmapArray = np.zeros((cmapPoints,3))
    for cmapIdx in range(cmapPoints):
        #Compute the gray scale value to which this point corresponds
        gsValue = cmapIdx+tranLow
         
        #Easy part first--if saturated, put the pure color in
        if ((gsValue>satLow)and(gsValue<satHigh)):
            cmapArray[cmapIdx,:] = cmapRGB
             
        #Lower ramp up to saturation
        elif (gsValue <= satLow):
            #Cmpute transparency
            thisAlpha = np.float(cmapIdx) / np.float(loRampPts+0.0001)
            #Compute weights of gray versus color
            tmpGS = (1-thisAlpha)*gsValue
            tmpRGB = (thisAlpha)*cmapRGB
            #Make the colormap to be the weighted average 
            #(division by 1 implicit)
            for idx in range(3):
                cmapArray[cmapIdx,idx] = int(tmpGS)+tmpRGB[idx]
 
        #Upper ramp from saturation
        elif (gsValue >= satHigh):
            #Compute inverse transparency
            thisAlpha = np.float(gsValue-satHigh) / hiRampPts
            #Compute weights of gray versus color
            tmpGS = (thisAlpha)*gsValue
            tmpRGB = (1-thisAlpha)*cmapRGB
            #Make the colormap to be the weighted average 
            #(division by 1 implicit)
            for idx in range(3):
                cmapArray[cmapIdx,idx] = int(tmpGS)+tmpRGB[idx]
                     
                     
        #Go through the image, when the gray scale is in the range to switch, 
        # insert the colormap
        
    for viewer in viewerList:
        thisImg = viewer.getSliceImageData()
        imgInt = (thisImg/np.max(thisImg)*255).astype(np.int)
         
        imgRGB_Mapped = np.stack([imgInt,imgInt,imgInt],axis=2)
         
        for row in range(imgRGB_Mapped.shape[0]):
            for col in range(imgRGB_Mapped.shape[1]):
                thisValue = imgRGB_Mapped[row,col,0]
                if ((thisValue>satLow)and(thisValue<satHigh)):
                    cmapIdx = np.int(thisValue-satLow)
                    imgRGB_Mapped[row,col,::] = cmapArray[cmapIdx,::]
                     
    
        im = Image.fromarray((imgRGB_Mapped * 255).astype(np.uint8))
        data = im.tobytes("raw","RGB")
        qim = QImage(data, im.size[0], im.size[1], QImage.Format_RGB888)
        rotate = QTransform()
        rotate.rotate(270)
        qimg = qim.transformed(rotate)
        pix = QPixmap.fromImage(qimg)
        viewer.setImage(pix)       
        
def saveData(wl, ww, transparency, saturation):
    f = open('currentState.txt', 'w')
    f.write('window level: ' + str(wl.value()))
    f.write('\n')
    f.write('window width: ' + str(ww.value()))
    f.write('\n')
    f.write('transparency: ' + str(transparency.value()))
    f.write('\n')
    f.write('saturation: ' + str(saturation.value()))
    f.close()
    

                

#------------------------------------------------------------
# Main
#------------------------------------------------------------
        

def main(leftFile):
    global viewer1
    global viewer2
    global winwidthScrollbar
    global winlevelScrollbar
    global winwidthText
    global winlevelText  
    global horscrollbar
    global verscrollbar
    global openFileText1
    global openFileText2
    global crosshairsBox1
    global vlayout
    global chGroupBox
    global layout
    global thruplaneBox
    global slicescrollbar
    global slicesTextbox
    global verTextbox
    global horTextbox
    global window

    # Create the application.
    app = QApplication(sys.argv)
    
    window = QWidget()
    
    #-------------------------------------------------
    # Create the user interface objects
    #-------------------------------------------------
    # Create image viewer and load an image file to display.
    viewer1 = setup3D.QtImageViewer()
    viewer1.setFocus()
    viewer2 = setup3D.QtImageViewer()
    viewer2.setFocus()
    viewer3 = setup3D.QtImageViewer()
    viewer3.setFocus()
    
    if(leftFile != ''):
        viewer1.loadFile(leftFile)
        viewer2.loadFile(leftFile)
        viewer3.loadFile(leftFile)

    # Handle left mouse clicks with custom slot.
    viewer1.leftMouseButtonPressed.connect(handleLeftClick)
    viewer2.leftMouseButtonPressed.connect(handleLeftClick)
    viewer3.leftMouseButtonPressed.connect(handleLeftClick)
    
    viewerList = [viewer1, viewer2, viewer3]
    
    
    # -----------------------------------------------
    openFileBtn1 = QPushButton()
    openFileBtn1.setFixedWidth(150)
    openFileBtn1.setText('Open Image')
    openFileText1 = QLineEdit()
    openFileText1.setFixedSize(300,20)
    crosshairsBox1 = QCheckBox()
    crosshairsBox1.setText('Enable Crosshairs')
    crosshairsBox1.setCheckState(0)
    
    # -----------------------------------------------
    saveBtn = QPushButton()
    saveBtn.setFixedWidth(150)
    saveBtn.setText('Save')
    
    
    # -----------------------------------------------
    horLabel = QLabel()
    horLabel.setText('Horizontal Profile')
    horscrollbar = QScrollBar()
    horscrollbar.setOrientation(1)
    horTextbox = QLineEdit()
    horTextbox.setFixedSize(50, 20)
    horTextbox.setText(str(viewer1.getHorizVal()+1))
    
    horscrollbar.setMinimum(1)
    horscrollbar.setMaximum(int(viewer1.getImgHeight()))
    horscrollbar.setValue(viewer1.getHorizVal())
    horscrollbar.setPageStep(1)
    
    
    verLabel = QLabel()
    verLabel.setText('Vertical Profile')
    verscrollbar = QScrollBar()
    verscrollbar.setOrientation(1)
    verTextbox = QLineEdit()
    verTextbox.setFixedSize(50, 20)
    verTextbox.setText(str(viewer1.getVertVal()+1))
    
    verscrollbar.setMinimum(1)
    verscrollbar.setMaximum(int(viewer1.getImgWidth()))
    verscrollbar.setValue(viewer1.getVertVal())
    verscrollbar.setPageStep(1)
    
    thruplaneBox = QCheckBox()
    thruplaneBox.setText('Enable Through-Planne')
    thruplaneBox.setCheckState(0)
    
    
    chGroupBox = QGroupBox("Crosshair Profile")
    layouts = QVBoxLayout()
    layouts.addWidget(horLabel)
    layouts.addWidget(horscrollbar)
    layouts.addWidget(horTextbox)
    layouts.addWidget(verLabel)
    layouts.addWidget(verscrollbar)
    layouts.addWidget(verTextbox)
    layouts.addWidget(thruplaneBox)
    chGroupBox.setLayout(layouts)
    
    # -----------------------------------------------
    
    slicesLabel1 = QLabel()
    slicesLabel1.setText('Image 1')
    slicesTextbox1 = QLineEdit()
    slicesTextbox1.setFixedSize(50, 20)
    slicescrollbar1 = QScrollBar()
    slicescrollbar1.setOrientation(1)
     
    slicescrollbar1.setMinimum(viewer1.getSliceMin())
    slicescrollbar1.setMaximum(viewer1.getSliceMax())
    slicescrollbar1.setValue(viewer1.getCurSlice())
    slicescrollbar1.setPageStep(1)
    slicesTextbox1.setText(str(viewer1.getCurSlice()))
    
    
    slicesLabel2 = QLabel()
    slicesLabel2.setText('Image 2')
    slicesTextbox2 = QLineEdit()
    slicesTextbox2.setFixedSize(50, 20)
    slicescrollbar2 = QScrollBar()
    slicescrollbar2.setOrientation(1)
     
    slicescrollbar2.setMinimum(viewer2.getSliceMin())
    slicescrollbar2.setMaximum(viewer2.getSliceMax())
    slicescrollbar2.setValue(viewer2.getCurSlice())
    slicescrollbar2.setPageStep(1)
    slicesTextbox2.setText(str(viewer2.getCurSlice()))
    
    
    slicesLabel3 = QLabel()
    slicesLabel3.setText('Image 3')
    slicesTextbox3 = QLineEdit()
    slicesTextbox3.setFixedSize(50, 20)
    slicescrollbar3 = QScrollBar()
    slicescrollbar3.setOrientation(1)
     
    slicescrollbar3.setMinimum(viewer3.getSliceMin())
    slicescrollbar3.setMaximum(viewer3.getSliceMax())
    slicescrollbar3.setValue(viewer3.getCurSlice())
    slicescrollbar3.setPageStep(1)
    slicesTextbox3.setText(str(viewer3.getCurSlice()))
    
    
    # -----------------------------------------------
    # window level, window width adjust
    wwMin, wwMax = viewer1.getWinWidthRange()
    wlMin, wlMax = viewer1.getWinLevelRange()
 
    wwValue = viewer1.getWindowWidth()
    wlValue = viewer1.getWindowLevel() 
     
     
    winwidthLabel = QLabel()
    winwidthLabel.setText('Window Max')
    winwidthText = QLineEdit()
    winwidthText.setFixedSize(80, 20)
    winwidthScrollbar = QScrollBar()
    winwidthScrollbar.setOrientation(1)
    winwidthScrollbar.setMinimum(wwMin)
    winwidthScrollbar.setMaximum(wwMax)   
    winwidthScrollbar.setPageStep(1)
     
    winlevelLabel = QLabel()
    winlevelLabel.setText('Window Min')    
    winlevelText = QLineEdit()
    winlevelText.setFixedSize(80, 20)
    winlevelScrollbar = QScrollBar()
    winlevelScrollbar.setOrientation(1)
    winlevelScrollbar.setMinimum(wlMin)
    winlevelScrollbar.setMaximum(wlMax) 
    winlevelScrollbar.setPageStep(1)
     
     
    winwidthScrollbar.setValue(round(wwValue,4)+1) 
    winlevelScrollbar.setValue(round(wlMin,4)) 
     
     
    winlevelText.setValidator
    winwidthText.setValidator
    winwidthText.setText(str(round(wwValue,4)+1))
    winlevelText.setText(str(round(wlMin,4)))  
       
    viewer1.setWindowWidth(round(wwValue,4)+1)
    viewer1.setWindowLevel(wlMin)  
     
    # -----------------------------------------------
     
    ortlist1 = QComboBox()
    ortlabel1 = QLabel()
    ortlabel1.setText('Image 1')   
    ortlist1.addItem('Dim 1 vs Dim 2')
    ortlist1.addItem('Dim 1 vs Dim 3')
    ortlist1.addItem('Dim 2 vs Dim 3')
    
    ortlist2 = QComboBox()
    ortlabel2 = QLabel()
    ortlabel2.setText('Image 2') 
    ortlist2.addItem('Dim 1 vs Dim 2')
    ortlist2.addItem('Dim 1 vs Dim 3')
    ortlist2.addItem('Dim 2 vs Dim 3')
    
    ortlist3 = QComboBox()
    ortlabel3 = QLabel()
    ortlabel3.setText('Image 3') 
    ortlist3.addItem('Dim 1 vs Dim 2')
    ortlist3.addItem('Dim 1 vs Dim 3')
    ortlist3.addItem('Dim 2 vs Dim 3')
        
    # -----------------------------------------------
    
    # -------- Transparency 
    transUp1 = QPushButton()
    transUp1.setFixedWidth(50)
    transUp1.setText('+')
    transDown1 = QPushButton()
    transDown1.setFixedWidth(50)
    transDown1.setText('-')
    transUp2 = QPushButton()
    transUp2.setFixedWidth(50)
    transUp2.setText('+')
    transDown2 = QPushButton()
    transDown2.setFixedWidth(50)
    transDown2.setText('-')
    transparencyLabel = QLabel("Center")
    transparencyLabel.setText("Low/High Transparency")
    transparency = RangeSlider(Qt.Orientation.Vertical)
    transparency.setMinimum(0)
    transparency.setMaximum(255)
    transparency.setLow(0)
    transparency.setHigh(255)
    transTextbox = QLineEdit()
    transTextbox.setAlignment(Qt.AlignCenter)
    transTextbox.setFixedSize(80, 20)
    
    # -------- Saturation
    satUp1 = QPushButton()
    satUp1.setFixedWidth(50)
    satUp1.setText('+')
    satDown1 = QPushButton()
    satDown1.setFixedWidth(50)
    satDown1.setText('-')
    satUp2 = QPushButton()
    satUp2.setFixedWidth(50)
    satUp2.setText('+')
    satDown2 = QPushButton()
    satDown2.setFixedWidth(50)
    satDown2.setText('-')
    saturationLabel = QLabel("Center")
    saturationLabel.setText("Min/Max Saturation")
    saturation = RangeSlider(Qt.Orientation.Vertical)
    saturation.setMinimum(0)
    saturation.setMaximum(255)
    saturation.setLow(0)
    saturation.setHigh(255)
    satTextbox = QLineEdit()
    satTextbox.setAlignment(Qt.AlignCenter)
    satTextbox.setFixedSize(80, 20)
    
    
    # -----------------------------------------------
    openFileBtn1.clicked.connect(btn1Click)
    
    saveBtn.clicked.connect( lambda: saveData(winlevelScrollbar, winwidthScrollbar, transparency, saturation) )
    
    slicescrollbar1.valueChanged.connect( lambda: slicescrollbarChange(viewer1, slicesTextbox1, slicescrollbar1.value(),transparency, saturation) )
    slicesTextbox1.returnPressed.connect( lambda: slicetextEditChange(viewer1, slicescrollbar1, slicesTextbox1.text(),transparency, saturation) )
    slicescrollbar2.valueChanged.connect( lambda: slicescrollbarChange(viewer2, slicesTextbox2, slicescrollbar2.value(),transparency, saturation) )
    slicesTextbox2.returnPressed.connect( lambda: slicetextEditChange(viewer2, slicescrollbar2, slicesTextbox2.text(),transparency, saturation) )
    slicescrollbar3.valueChanged.connect( lambda: slicescrollbarChange(viewer3, slicesTextbox3, slicescrollbar3.value(),transparency, saturation) )
    slicesTextbox3.returnPressed.connect( lambda: slicetextEditChange(viewer3, slicescrollbar3, slicesTextbox3.text(),transparency, saturation) )
    
    
    winlevelScrollbar.valueChanged.connect(lambda: wlscrollchange(viewerList, winlevelScrollbar.value(),winlevelText,transparency, saturation))
    winwidthScrollbar.valueChanged.connect(lambda: wwscrollchange(viewerList, winwidthScrollbar.value(),winwidthText,transparency, saturation))
    
    winlevelText.returnPressed.connect(lambda: wltextchange(viewerList, winlevelText.text(),winlevelText,transparency, saturation))
    winwidthText.returnPressed.connect(lambda: wwtextchange(viewerList, winwidthText.text(),winwidthText,transparency, saturation))
    
    
    ortlist1.currentIndexChanged.connect(lambda: ortChange(viewer1, slicescrollbar1, slicesTextbox1, verscrollbar, verTextbox,
                                                          horscrollbar, horTextbox, crosshairsBox1, ortlist1.currentIndex()) ) 
    ortlist2.currentIndexChanged.connect(lambda: ortChange(viewer2, slicescrollbar2, slicesTextbox2, verscrollbar, verTextbox,
                                                          horscrollbar, horTextbox, crosshairsBox1, ortlist2.currentIndex()) ) 
    ortlist3.currentIndexChanged.connect(lambda: ortChange(viewer3, slicescrollbar3, slicesTextbox3, verscrollbar, verTextbox,
                                                          horscrollbar, horTextbox, crosshairsBox1, ortlist3.currentIndex()) ) 
    
    
    crosshairsBox1.toggled.connect(enableCrosshair)
    
    
    horscrollbar.valueChanged.connect(horizScrollChange)
    horTextbox.returnPressed.connect(horizTextChange) 
    verscrollbar.valueChanged.connect(vertScrollChange)
    verTextbox.returnPressed.connect(vertTextChange)
    thruplaneBox.toggled.connect(enableThroughPlane)

    
    transparency.sliderMoved.connect(lambda: colormap(viewerList, transparency, saturation))
#     transTextbox.returnPressed.connect(lambda: colormap(viewerList, transTextbox, saturation))
    
    transUp1.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, 1,'high', 'transparency'))
    transDown1.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, -1,'high', 'transparency'))
    transUp2.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, 1, 'low', 'transparency'))
    transDown2.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, -1, 'low', 'transparency'))
    

    saturation.sliderMoved.connect(lambda: colormap(viewerList, transparency, saturation))
#     satTextbox.returnPressed.connect(lambda: colormap(viewerList, transparency, satTextbox))
    
    satUp1.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, 1, 'high', 'saturation'))
    satDown1.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, -1, 'high', 'saturation'))
    satUp2.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, 1, 'low', 'saturation'))
    satDown2.clicked.connect(lambda: colormapIncrement(viewerList, transparency, saturation, -1, 'low', 'saturation'))

    
    
    
    # -------------------------------------------------
    # Do layout 
    # -------------------------------------------------    
    vlayout = QVBoxLayout()
    layoutop = QGridLayout()  
    layoutop.setColumnStretch(1, 3)
    layoutop.setColumnStretch(2, 3)     
    layoutop.addWidget(openFileBtn1, 0,0)
    layoutop.addWidget(openFileText1, 1,0)
    
    displayGroupBox = QGroupBox("Display")
    layout = QGridLayout()
    layout.setColumnStretch(1, 4)
    layout.setColumnStretch(2, 4)    
    layout.addWidget(winwidthLabel, 0, 0)
    layout.addWidget(winwidthScrollbar, 0, 1)
    layout.addWidget(winwidthText, 0, 2)
    layout.addWidget(winlevelLabel, 1, 0)
    layout.addWidget(winlevelScrollbar, 1, 1)
    layout.addWidget(winlevelText, 1, 2)
    displayGroupBox.setLayout(layout)
    
    sliceGroupBox = QGroupBox("Set Slices")
    layouts = QGridLayout() 
    layouts.addWidget(slicesLabel1, 0, 0, 1, 1)
    layouts.addWidget(slicesTextbox1, 0, 1, 1, 1)
    layouts.addWidget(slicescrollbar1,1, 0, 1, 2)
    layouts.addWidget(slicesLabel2, 2, 0, 1, 1)
    layouts.addWidget(slicesTextbox2, 2, 1, 1, 1)
    layouts.addWidget(slicescrollbar2, 3, 0, 1, 2)
    layouts.addWidget(slicesLabel3, 4, 0, 1, 1)
    layouts.addWidget(slicesTextbox3, 4, 1, 1, 1)
    layouts.addWidget(slicescrollbar3, 5, 0, 1, 2)
    sliceGroupBox.setLayout(layouts)
    
    ortGroupBox = QGroupBox("Set Orientation")
    layouts = QGridLayout()
    layouts.addWidget(ortlabel1, 0, 0, 1, 2)
    layouts.addWidget(ortlist1, 1, 0, 1, 2)
    layouts.addWidget(ortlabel2, 0, 2, 1, 2)
    layouts.addWidget(ortlist2, 1, 2, 1, 2)
    layouts.addWidget(ortlabel3, 0, 4, 1, 2)
    layouts.addWidget(ortlist3, 1, 4, 1, 2)
    ortGroupBox.setLayout(layouts)
    
    transGroupBox = QGroupBox("Set Sliders")
    layout = QGridLayout()
    layout.setRowStretch(0, 10) 
    layout.setRowStretch(1, 10) 
    layout.setRowStretch(2, 10) 
    layout.setRowStretch(3, 10) 
    layout.setRowStretch(4, 10) 
    layout.addWidget(transparencyLabel,0,0,1,3,alignment=Qt.AlignCenter)
    layout.addWidget(transTextbox,1,0,1,3,alignment=Qt.AlignCenter)
    layout.addWidget(transUp1,2,0,1,1,alignment=Qt.AlignCenter)
    layout.addWidget(transDown1,2,1,1,1,alignment=Qt.AlignLeft)
    layout.addWidget(transUp2,4,0,1,1,alignment=Qt.AlignCenter)
    layout.addWidget(transDown2,4,1,1,1,alignment=Qt.AlignLeft)
    layout.addWidget(transparency,2,2,3,1,alignment=Qt.AlignLeft)
    layout.addWidget(saturationLabel,0,4,1,3,alignment=Qt.AlignCenter)
    layout.addWidget(satTextbox,1,4,1,3,alignment=Qt.AlignCenter)
    layout.addWidget(satUp1,2,4,1,1,alignment=Qt.AlignCenter)
    layout.addWidget(satDown1,2,5,1,1,alignment=Qt.AlignLeft)
    layout.addWidget(satUp2,4,4,1,1,alignment=Qt.AlignCenter)
    layout.addWidget(satDown2,4,5,1,1,alignment=Qt.AlignLeft)
    layout.addWidget(saturation,2,6,3,1,alignment=Qt.AlignLeft)
    transGroupBox.setLayout(layout)
    
    layoutbtm = QGridLayout()  
    layoutbtm.addWidget(saveBtn, 0,0)
    
    
    vlayout.addLayout(layoutop) 
    vlayout.addSpacing(20)
    vlayout.addWidget(displayGroupBox)
    vlayout.addSpacing(10)
    vlayout.addWidget(sliceGroupBox)
    vlayout.addSpacing(10)
    vlayout.addWidget(ortGroupBox)
    vlayout.addSpacing(10)
    vlayout.addWidget(transGroupBox)
    vlayout.addSpacing(10)
    vlayout.addWidget(crosshairsBox1)  
    vlayout.addSpacing(10)      
    vlayout.addLayout(layoutbtm)
    vlayout.addStretch(1)
    
    hlayout = QHBoxLayout()
    hlayout.addWidget(viewer1)
    hlayout.addWidget(viewer2)
    hlayout.addWidget(viewer3)
    hlayout.addLayout(vlayout)
    
    window.setLayout(hlayout)
    
    window.show()
    
    app.exec_()
    app.quit()
    
#MAIN
if __name__ == '__main__':
    
    global args
    parseArgs()
    
    main(args.left)
