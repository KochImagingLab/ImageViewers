#! /usr/bin/env python3
""" 
QtImageViewer.py: PyQt image viewer widget for a QPixmap in a QGraphicsView scene with mouse zooming and panning.

"""

import os.path
import os
import sys 
import argparse

import numpy as np
import nibabel as nib
import SimpleITK as sitk
import SegmenterSetup
import PyQt5

from PyQt5.QtCore import Qt, QRectF, pyqtSignal, QT_VERSION_STR, QLineF, QRegExp, QObject, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QPainterPath, QPainter, QPen, QColor, QIntValidator, QTransform
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QGroupBox,\
                            QHBoxLayout, QVBoxLayout, QGridLayout, QWidget, QLineEdit,QPushButton,\
                            QGraphicsLineItem, QScrollBar, QCheckBox, QComboBox, QAbstractItemView, QLabel
from PyQt5.QtWidgets import QApplication


#------------------------------------------------------------
# Event handling
#------------------------------------------------------------
        
def parseArgs():
    #parse all of the passed in arguments
    global args
    parser = argparse.ArgumentParser(description='Input parameters')
    parser.add_argument('-n', '--niiFile', help='Path to nifti file', default='') 

    parser.add_argument('-o', '--outFile', help='Path to output file prefix', default='')

    parser.add_argument('-p', '--inPlane', help='Initial Scan Plane [1,2,3]', default='')

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
    
    
#    horscrollbar.setMinimum(1)
#    horscrollbar.setMaximum(int(viewer1.getImgHeight()))
#    horscrollbar.setValue(viewer1.getHorizVal())
#    horscrollbar.setPageStep(1)
#
#    verscrollbar.setMinimum(1)
#    verscrollbar.setMaximum(int(viewer1.getImgWidth()))
#    verscrollbar.setValue(viewer1.getVertVal())
#    verscrollbar.setPageStep(1)
#
      
    
    openFileText1.setText(fileName)
    
def procThreeD():
    global viewer1
#    global horscrollbar
#    global verscrollbar
    global threeDBox1
    
    global procThree
    
    procThree = threeDBox1.checkState()
    
    print('Into 3D Proc Changer')
    print(procThree)
#    global vlayout
#    global chGroupBox
#    global layout
#    global thruplaneBox
#
#    viewer1.setVertVal(viewer1.getImgWidth() // 2)
#    viewer1.setHorizVal(viewer1.getImgHeight() // 2)
#
#    state = viewer1.setCrosshair(crosshairsBox1.checkState())
#
#    if(state != 0):
#        if(crosshairsBox1.checkState() == 2):
#            verscrollbar.setValue(viewer1.getVertVal())
#            horscrollbar.setValue(viewer1.getHorizVal())
#            vlayout.addWidget(chGroupBox)
#        else:
#            layout.removeWidget(chGroupBox)
#            chGroupBox.setParent(None)
#            thruplaneBox.setCheckState(0)
        
        
#def enableThroughPlane():
#
#    global viewer1
#    global thruplaneBox
#
#    viewer1.setThruPlane(thruplaneBox.checkState())
        
    
def handleLeftClick(x, y):
    global viewer1
    global procThree
    global thSet
    
    row = int(y)
    column = int(x)
    
    if( 0 <= row < viewer1.getImgHeight() and 0 <= column < viewer1.getImgWidth()):
        print('Button Clicked')
        print(thSet)
        viewer1.segmentImageCallback(row,column,thSet,procThree)
        #print(viewer1.getImageMaximum())
        #horizScrollChange(row)
        #vertScrollChange(column)
        
def slicescrollbarChange(value):
    global viewer1
    global slicesTextbox
    
    viewer1.setSlice(value)
    slicesTextbox.setText(str(value))     

def threshscrollbarChange(value):
    global viewer1
    global thTextbox
    global thSet

    thSet = value/100.0
    thTextbox.setText(str(value))
        

def slicetextEditChange():
    global viewer1
    global slicesTextbox
    global slicescrollbar
    
    value = slicesTextbox.text()
    if int(value)<0:
        value = 0
    elif int(value)>viewer1.getSliceMax():
        value = viewer1.getSliceMax()
        
    viewer1.setSlice(int(value))
    slicescrollbar.setValue(int(value))   
    
def wlscrollchange(value):
    global wlMin
    global wlMax
    global wlValue
    global viewer1
    global winlevelText 
    
    wlValue = float(value)         
    
    viewer1.setWindowLevel(wlValue)
    winlevelText.setText(str(round(wlValue,4)))
    
def wwscrollchange(value):
    global wwMin
    global wwMax
    global wwValue 
    global viewer1
    global winwidthText
    
    wwValue = float(value)       
    
    viewer1.setWindowWidth(wwValue)
    
    winwidthText.setText(str(round(wwValue,4)))
    
def wltextchange():
    global wlMins
    global wlMax
    global wlValue 
    global viewer1
    global winlevelText
    
    value = winlevelText.text()
           
    try:
        wlValue = float(value)
    except:
        wlValue = float(0)
    viewer1.setWindowLevel(wlValue)
    
    winlevelText.setText(str(round(wlValue,4)))

def wwtextchange():
    global wwMin
    global wwMax
    global wwValue
    global viewer1
    global winwidthText 
    
    value = winwidthText.text()
    
    try:
        wwValue = float(value)
    except:
        wwValue = float(0)
        
    viewer1.setWindowWidth(wwValue)
    winwidthText.setText(str(round(wwValue,4)))
    
def ortChange(value):
    global viewer1
    global slicescrollbar
    global slicesTextbox
  #  global verscrollbar
  #  global verTextbox
  #  global horscrollbar
  #  global horTextbox
  #  global crosshairsBox1
    
    viewer1.setSliceOrientation(value+1)
    print('OrtChange Hit')
    if (viewer1._pixmapHandle is not None): 
        slicescrollbar.setMaximum(viewer1.getSliceMax())
        slicescrollbar.setValue(viewer1.getCurSlice())
        slicesTextbox.setText(str(viewer1.getCurSlice()))   
        
#        verscrollbar.setMaximum(int(viewer1.getImgWidth()))
#
#
#        viewer1.setVertVal(viewer1.getImgWidth() // 2)
#        viewer1.setHorizVal(viewer1.getImgHeight() // 2)
#
#        vertVal = viewer1.getVertVal()
#        horzVal = viewer1.getHorizVal()
#
#        verTextbox.setText(str(vertVal))
#        verscrollbar.setValue(int(vertVal))
#        if(crosshairsBox1.checkState() == 2):
#            viewer1.updateVerticalProfile(int(vertVal))
#
#        horscrollbar.setMaximum(int(viewer1.getImgHeight()))
#        horTextbox.setText(str(horzVal))
#        horscrollbar.setValue(int(horzVal))
#        if(crosshairsBox1.checkState() == 2):
#            viewer1.updateHorizontalProfile(int(horzVal))
        
#
#def horizScrollChange(value):
#    global viewer1
#    global horscrollbar
#    global horTextbox
#    global crosshairsBox1
#
#    if(crosshairsBox1.checkState() == 2):
#        viewer1.updateHorizontalProfile(int(value)-1)
#    horTextbox.setText(str(int(value)))
#    horscrollbar.setValue(int(value))
#
#def horizTextChange():
#    global viewer1
#    global horscrollbar
#    global horTextbox
#    global crosshairsBox1
#
#    value = horTextbox.text()
#    if(crosshairsBox1.checkState() == 2):
#        viewer1.updateHorizontalProfile(int(value)-1)
#    horTextbox.setText(str(int(value)))
#    horscrollbar.setValue(int(value))
#
#def vertScrollChange(value):
#    global viewer1
#    global verscrollbar
#    global verTextbox
#    global crosshairsBox1
#
#    if(crosshairsBox1.checkState() == 2):
#        viewer1.updateVerticalProfile(int(value)-1)
#    verTextbox.setText(str(int(value)))
#    verscrollbar.setValue(int(value))
#
#def vertTextChange():
#    global viewer1
#    global verscrollbar
#    global verTextbox
#    global crosshairsBox1
#
#    value = verTextbox.text()
#    if(crosshairsBox1.checkState() == 2):
#        viewer1.updateVerticalProfile(int(value)-1)
#    verTextbox.setText(str(int(value)))
#    verscrollbar.setValue(int(value))


#------------------------------------------------------------
# Main
#------------------------------------------------------------
        

def main(thisFile,outFile,inPlane):
    global viewer1
    global winwidthScrollbar
    global winlevelScrollbar
    global winwidthText
    global winlevelText  
    global threshscrollbar
    #global verscrollbar
    global openFileText1
    global threeDBox1
    global vlayout
    global chGroupBox
    global layout
    #global thruplaneBox
    global slicescrollbar
    global slicesTextbox
    global thTextbox
    global thSet
    #global horTextbox
    global window
    global procThree
    
    procThree = 0
    thSet = 0.5
    
 
    # Create the application.
    app = QApplication(sys.argv)
     
    window = QWidget()
     
    #-------------------------------------------------
    # Create the user interface objects
    #-------------------------------------------------
    # Create image viewer and load an image file to display.
    viewer1 = SegmenterSetup.QtImageViewer()
    viewer1.setSceneRect(QRectF(0,0,800,800))
    viewer1.setFocus()
     
    if(thisFile != ''):
        viewer1.loadNIFTI(thisFile)
 
    # Handle left mouse clicks with custom slot.
    viewer1.leftMouseButtonPressed.connect(handleLeftClick)
     
    # -----------------------------------------------
    openFileBtn1 = QPushButton()
    openFileBtn1.setFixedWidth(120)
    openFileBtn1.setText('Open Image')
    openFileText1 = QLineEdit()
    openFileText1.setFixedSize(300,20)
    threeDBox1 = QCheckBox()
    threeDBox1.setText('3D Segmentation')
    threeDBox1.setCheckState(0)
#
     
#    # -----------------------------------------------
    thLabel = QLabel()
    thLabel.setText('Threshold Scale [0, 100%]')
    threshscrollbar = QScrollBar()
    threshscrollbar.setOrientation(1)
    thTextbox = QLineEdit()
    thTextbox.setFixedSize(50, 20)
    thTextbox.setText(str(50))

    threshscrollbar.setMinimum(0)
    threshscrollbar.setMaximum(100)
    threshscrollbar.setValue(50)
    threshscrollbar.setPageStep(1)
#
#
#    verLabel = QLabel()
#    verLabel.setText('Vertical Profile')
#    verscrollbar = QScrollBar()
#    verscrollbar.setOrientation(1)
#    verTextbox = QLineEdit()
#    verTextbox.setFixedSize(50, 20)
#    verTextbox.setText(str(viewer1.getVertVal()+1))
#
#    verscrollbar.setMinimum(1)
#    verscrollbar.setMaximum(int(viewer1.getImgWidth()))
#    verscrollbar.setValue(viewer1.getVertVal())
#    verscrollbar.setPageStep(1)
#
#    thruplaneBox = QCheckBox()
#    thruplaneBox.setText('Enable Through-Planne')
#    thruplaneBox.setCheckState(0)
#
#
#    chGroupBox = QGroupBox("Crosshair Profile")
#    layouts = QVBoxLayout()
#    layouts.addWidget(thLabel)
#    layouts.addWidget(threshscrollbar)
#    layouts.addWidget(horTextbox)
#    layouts.addWidget(verLabel)
#    layouts.addWidget(verscrollbar)
#    layouts.addWidget(verTextbox)
#    layouts.addWidget(thruplaneBox)
#    chGroupBox.setLayout(layouts)
#
    # -----------------------------------------------
    slicesTextbox = QLineEdit()
    slicesTextbox.setFixedSize(50, 20)
    slicescrollbar = QScrollBar()
    slicescrollbar.setOrientation(1)
     
    slicescrollbar.setMinimum(viewer1.getSliceMin())
    slicescrollbar.setMaximum(viewer1.getSliceMax())
    slicescrollbar.setValue(viewer1.getCurSlice())
    slicescrollbar.setPageStep(1)
    slicesTextbox.setText(str(viewer1.getCurSlice()))
     
    # -----------------------------------------------
    # window level, window width adjust
    wwMin = viewer1.getWinWidthRange()[0]
    wwMax = viewer1.getWinWidthRange()[1]
    wlMin = viewer1.getWinLevelRange()[0]
    wlMax = viewer1.getWinLevelRange()[1]
 
    wwValue = viewer1.getWindowWidth()
    wlValue = viewer1.getWindowLevel() 
     
     
    winwidthLabel = QLabel()
    winwidthLabel.setText('Window Max')
    winwidthText = QLineEdit()
    winwidthText.setFixedSize(80, 20)
    winwidthScrollbar = QScrollBar()
    winwidthScrollbar.setOrientation(1)
    winwidthScrollbar.setMinimum(0)
    winwidthScrollbar.setMaximum(999)   
    winwidthScrollbar.setPageStep(1)
     
    winlevelLabel = QLabel()
    winlevelLabel.setText('Window Min')    
    winlevelText = QLineEdit()
    winlevelText.setFixedSize(80, 20)
    winlevelScrollbar = QScrollBar()
    winlevelScrollbar.setOrientation(1)
    winlevelScrollbar.setMinimum(0)
    winlevelScrollbar.setMaximum(999) 
    winlevelScrollbar.setPageStep(1)
     
     
    winwidthScrollbar.setValue(round(wwValue,4)+1) 
    winlevelScrollbar.setValue(round(wlMin,4)) 
     
     
    winlevelText.setValidator
    winwidthText.setValidator
    winwidthText.setText(str(round(wwValue,4)+1))
    winlevelText.setText(str(round(wlMin,4)))  
       
    viewer1.setWindowWidth(round(wwValue,4)+1)
    viewer1.setWindowLevel(wlMin)  
     
    ortlist = QComboBox()
    ortlist.addItem('Dim 1 vs Dim 2')
    ortlist.addItem('Dim 1 vs Dim 3')
    ortlist.addItem('Dim 2 vs Dim 3')
    ortlist.setCurrentIndex(int(inPlane))
    
    viewer1.setSliceOrientation(int(inPlane)+1)
     
    # -----------------------------------------------
    openFileBtn1.clicked.connect(btn1Click)
    slicescrollbar.valueChanged.connect(slicescrollbarChange)
    threshscrollbar.valueChanged.connect(threshscrollbarChange)
    slicesTextbox.returnPressed.connect(slicetextEditChange)
    winlevelScrollbar.valueChanged.connect(wlscrollchange)
    winwidthScrollbar.valueChanged.connect(wwscrollchange)
    winlevelText.returnPressed.connect(wltextchange)
    winwidthText.returnPressed.connect(wwtextchange)  
    ortlist.currentIndexChanged.connect(ortChange)
    threeDBox1.toggled.connect(procThreeD)
    
    ortChange(int(inPlane))
     
     
#    horscrollbar.valueChanged.connect(horizScrollChange)
#    horTextbox.returnPressed.connect(horizTextChange)
#    verscrollbar.valueChanged.connect(vertScrollChange)
#    verTextbox.returnPressed.connect(vertTextChange)
#    thruplaneBox.toggled.connect(enableThroughPlane)
#
     
     
     
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
     
    sliceGroupBox = QGroupBox("Slices")
    layouts = QVBoxLayout()
    layouts.addWidget(slicesTextbox)
    layouts.addWidget(slicescrollbar)
    sliceGroupBox.setLayout(layouts)
    
    threshGroupBox = QGroupBox("Threshold [0, 100%]")
    layoutT = QVBoxLayout()
    layoutT.addWidget(thTextbox)
    layoutT.addWidget(threshscrollbar)
    threshGroupBox.setLayout(layoutT)
    
    
    vlayout.addLayout(layoutop) 
    vlayout.addSpacing(20)
    vlayout.addWidget(displayGroupBox)
    vlayout.addSpacing(10)
    vlayout.addWidget(sliceGroupBox)
    vlayout.addSpacing(10)
    vlayout.addWidget(ortlist)
    vlayout.addSpacing(10)
    vlayout.addWidget(threeDBox1)
    vlayout.addSpacing(10)
    vlayout.addWidget(threshGroupBox)
    vlayout.addStretch(1)
    vlayout.addSpacing(20)
    
    hlayout = QHBoxLayout()
    hlayout.addWidget(viewer1)
    hlayout.addLayout(vlayout)
     
    window.setLayout(hlayout)
     
    window.show()
     
    app.exec_()
    
    viewer1.writeOutputFiles(outFile)
    
    print('Exiting')
    
    app.quit()
    
#MAIN
if __name__ == '__main__':
    
    global args
    parseArgs()
    
    main(args.niiFile,args.outFile,args.inPlane)
