# -*- coding: utf-8 -*-
"""
/***************************************************************************
 EMProfilerDialog
                                 A QGIS plugin
 Makes channel profiles for EM lines
                             -------------------
        begin                : 2015-05-08
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Alex Brown
        email                : sdgdg
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import numpy as np
import matplotlib.pyplot as plot
import csv
import os
import subprocess
import math
from matplotlib.backends.backend_pdf import PdfPages
import sys
import threading

from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtCore import QObject
sys.excepthook = sys.__excepthook__
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'EMProfiler_dialog_base.ui'))


class EMProfilerDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(EMProfilerDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
       
        self.datafile = None
        self.delimiter = "comma"
        self.headerdict = {}
        self.lineCount = 0
         #initialise parameters THIS MAY NOW BE OBSOLETE
        self.outfilepath = None
        self.outfileDir = None
        self.outfileBase = None
        self.lineIdx = None
        self.coordIdx = None
        self.channelIdx = []
        self.DTMIdx = None
        self.loopheightIdx = None
        self.magIdx = None
        self.hiliteColour = "red"
        self.lineColour = "black"
        self.titleBase = None
        self.yLab = None
        self.xLab = None
        
        #these may not be necessary
        self.plotDTM = False
        self.plotLoopheight = False
        self.plotMag= False
        self.heightfromAltimeter = False
        self.hiliteCh = True
        
        #initialise the profile class
        self.profiler = ProfileMaker()
        
        
        #set default parameters, populate settings combo boxes
        self.sbxHilite.setValue(5)
        self.cbxHicol.addItems(['black', 'blue', 'cyan', 'green', 'magenta', 'red', 'yellow'])
        self.cbxHicol.setCurrentIndex(5)
        self.cbxLinecol.addItems(['black', 'blue', 'cyan', 'green', 'magenta', 'red', 'yellow'])
        self.cbxLinecol.setCurrentIndex(0)
        
        #link up buttons
        self.btnInpBrow.clicked.connect(self.showFileBrowser)
        self.btnOutfilebrow.clicked.connect(lambda: self.showSaveFile("Single"))
        self.btnOutdirbrow.clicked.connect(lambda: self.showSaveFile("Multi"))
        self.btnLoadInfo.clicked.connect(self.loadInfo)
        self.btnAddCh.clicked.connect(self.addChannels)
        self.btnRemCh.clicked.connect(self.remChannels)
        self.btnCreateProf.clicked.connect(self.makeProfiles)
        
        #Connect GUI elements with profiler parameters
        self.ledInput.textChanged.connect(lambda: self.setVariables(self.profiler, "datafile", self.ledInput.text()))
        self.ledOutfile.textChanged.connect(lambda: self.setVariables(self.profiler, "outfilepath", self.ledOutfile.text()))
        self.ledOutdir.textChanged.connect(lambda: self.setVariables(self.profiler, "outfiledir", self.ledOutdir.text()))
        self.ledTitle.textChanged.connect(lambda: self.setVariables(self.profiler, "titleBase", self.ledTitle.text()))
        self.ledXlab.textChanged.connect(lambda: self.setVariables(self.profiler, "xlabel", self.ledXlab.text()))
        self.ledYlab.textChanged.connect(lambda: self.setVariables(self.profiler, "ylabel", self.ledYlab.text()))
        self.cbxLine.currentIndexChanged.connect(lambda:self.setVariables(self.profiler, "lineIdx", self.cbxLine.currentText()))
        self.cbxCoord.currentIndexChanged.connect(lambda:self.setVariables(self.profiler, "coordIdx", self.cbxCoord.currentText()))
        self.cbxDTM.currentIndexChanged.connect(lambda:self.setVariables(self.profiler, "DTMIdx", self.cbxDTM.currentText()))
        self.cbxLoopHeight.currentIndexChanged.connect(lambda:self.setVariables(self.profiler, "loopheightIdx", self.cbxLoopHeight.currentText()))
        self.cbxMag.currentIndexChanged.connect(lambda:self.setVariables(self.profiler, "magIdx", self.cbxMag.currentText()))
        self.cbxHicol.currentIndexChanged.connect(lambda:self.setVariables(self.profiler, "hiliteColour", self.cbxHicol.currentText()))
        self.cbxLinecol.currentIndexChanged.connect(lambda:self.setVariables(self.profiler, "lineColour", self.cbxLinecol.currentText()))
        self.rbnComma.toggled.connect(lambda:self.setVariables(self.profiler, "delimiter", self.rbnComma.isChecked()))
        self.rbnSingle.toggled.connect(lambda:self.setVariables(self.profiler, "outstyle", self.rbnSingle.isChecked()))
        self.chkDTM.toggled.connect(lambda:self.setVariables(self.profiler, "plotDTM", self.chkDTM.isChecked()))
        self.chkMag.toggled.connect(lambda:self.setVariables(self.profiler, "plotMag", self.chkMag.isChecked()))
        self.chkLoopheight.toggled.connect(lambda:self.setVariables(self.profiler, "plotLoopheight", self.chkLoopheight.isChecked()))
        self.chkHilite.toggled.connect(lambda:self.setVariables(self.profiler, "hiliteCh", self.chkHilite.isChecked()))
        self.rbnRadar.toggled.connect(lambda:self.setVariables(self.profiler, "heightfromAltimeter", self.rbnRadar.isChecked()))
        self.sbxHilite.valueChanged.connect(lambda: self.setVariables(self.profiler, "hilitenchan", self.sbxHilite.value()))
        
        #listen for signals
        self.profiler.profilesStarted.connect(self.startProgress)
        self.profiler.profileCompleted.connect(self.updateProgress)
        self.profiler.numberofLines.connect(self.setNumberLines)
        
    def loadInfo(self):
        self.resetGUI()
        #open and read header data
        csvfile = open(self.datafile, 'rb')
        if self.delimiter == "comma":
            reader = csv.reader(csvfile)
        else:
            reader = csv.reader(csvfile, delimiter=" ", skipinitialspace=True)
        header = reader.next()
        headerdict = {}
        i=0
        for h in header:
            headerdict[h]=i
            i+=1
        self.headerdict = headerdict
        needsheaders = [self.lstAvailCh, self.cbxLine,
                        self.cbxCoord, self.cbxDTM,
                        self.cbxLoopHeight, self.cbxMag
                        ]
        #populate comboboxes and lists
        for tars in needsheaders:
                tars.clear()
        for keys in self.headerdict:
            for tars in needsheaders:
                tars.addItem(keys)
                
    def resetGUI(self):
        #reset gui elements 
        self.lstAvailCh.clear()
        self.lstSelCh.clear()
        self.sbxHilite.setValue(5)
        self.cbxHicol.addItems(['black', 'blue', 'cyan', 'green', 'magenta', 'red', 'yellow'])
        self.cbxHicol.setCurrentIndex(5)
        self.cbxLinecol.addItems(['black', 'blue', 'cyan', 'green', 'magenta', 'red', 'yellow'])
        self.cbxLinecol.setCurrentIndex(0)
        self.ledOutfile.clear()
        self.ledOutdir.clear()
        self.ledBasename.clear()
        self.chkHilite.setChecked(True)
        self.chkDTM.setChecked(False)
        self.chkLoopheight.setChecked(False)
        self.chkMag.setChecked(False)
        self.ledTitle.clear()
        self.ledXlab.clear()
        self.ledYlab.clear()
        
        #self.profiler = ProfileMaker()
        #reinstate some of the variables
        #self.profiler.datafile = os.path.normpath(self.ledInput.text())
        #if self.rbnComma.isChecked():
        #    self.profiler.delimiter = "comma"
        #else:
        #    self.profiler.delimiter = "space"
            
        #self.profiler.singleoutput = self.rbnSingle.isChecked()
        #Reset parameters to original state
        self.profiler.resetParameters()
        
        
    def addChannels(self):
        self.listMover(self.lstAvailCh, self.lstSelCh)
        self.updateChannelList() 
        
    def remChannels(self):
        self.listMover(self.lstSelCh, self.lstAvailCh)
        self.updateChannelList() 
        
    def listMover(self, source, target):
        for item in source.selectedItems():
            target.addItem(source.takeItem(source.row(item)))
            
    def updateChannelList(self):
        templist = []
        for i in xrange(self.lstSelCh.count()):
            templist.append(self.lstSelCh.item(i).text())
            
        self.profiler.channelIdx = []
        for j in templist:
            self.profiler.channelIdx.append(self.headerdict[j])
        self.profiler.channelIdx.sort()
                    
    def setVariables(self, target, variable, value):
        try:
            if variable == "datafile":
                target.datafile = os.path.normpath(value)
                self.datafile = os.path.normpath(value)
            elif variable == "delimiter":
                if value:
                    target.delimiter = "comma"
                    self.delimiter = "comma"
                else:
                    target.delimiter = "space"
                    self.delimiter = "space"
            elif variable == "outstyle":
                if value:
                    target.singleoutput = True
                else:
                    target.singleoutput = False
            elif variable == "outfilepath":
                target.outfilepath = os.path.normpath(value)
            elif variable == "outfileDir":
                target.outfileDir = os.path.normpath(value)
            elif variable == "outfilebase":
                target.outfileBase = value
            elif variable == "lineIdx":
                target.lineIdx = self.headerdict[value]
            elif variable == "coordIdx":
                target.coordIdx = self.headerdict[value]
            elif variable =="DTMIdx":
                target.DTMIdx = self.headerdict[value]
            elif variable == "loopheightIdx":
                target.loopheightIdx = self.headerdict[value]
            elif variable == "magIdx":
                target.magIdx = self.headerdict[value]
            elif variable == "hiliteColour":
                target.hiliteColour = value
            elif variable == "lineColour":
                target.lineColour = value
            elif variable == "titleBase":
                target.titleBase = value
            elif variable == "ylabel":
                target.yLab = value
            elif variable == "xlabel":
                target.xLab = value
            elif variable == "plotDTM":
                target.plotDTM = value
            elif variable == "plotLoopheight":
                target.plotLoopheight = value
            elif variable == "plotMag":
                target.plotMag = value
            elif variable == "hiliteCh":
                target.hiliteCh = value
            elif variable == "hilitenchan":
                target.hiliteNCh = value
            elif variable == "heightfromAltimeter":
                target.heightfromAltimeter = value
                
        except ValueError:
            pass
            
    def showFileBrowser(self):
    #call up a file browser with filter for extension. 

        self.ledInput.setText(QtGui.QFileDialog.getOpenFileName(self, 'Select EM Data file', "/", "*.csv *.XYZ *.txt"))
    
    def showSaveFile(self, target):
        if target == "Single":
            self.ledOutfile.setText(QtGui.QFileDialog.getSaveFileName(self, 'Save File', "/", "*.pdf"))
        elif target == "Multi":
            self.ledOutdir.setText(QtGui.QFileDialog.getExistingDirectory(self, 'Select Project Directory', "/",QtGui.QFileDialog.ShowDirsOnly))
    
    def setNumberLines(self, lines):
        self.lineCount = lines
        
    def startProgress(self):
        self.progressBar.reset()
        self.progressBar.setMaximum(self.lineCount)
        
    def updateProgress(self, progressCount):
        self.progressBar.setValue(progressCount)
        
    def makeProfiles(self):
        #run the code to generate profiles
        #self.profiler.run()
        #try creating a threading
        procthread = myThread(self.profiler)
        procthread.start()
    
class myThread(threading.Thread):
    def __init__(self, promakerinst):
        threading.Thread.__init__(self)
        self.inst = promakerinst
    def run(self):
        self.inst.run()
        
class ProfileMaker(QObject):

    numberofLines = QtCore.pyqtSignal(int)
    profileCompleted = QtCore.pyqtSignal(int)
    profilesStarted = QtCore.pyqtSignal()
    
    def __init__(self):
        super(ProfileMaker, self).__init__()
        #plotting parameters
        self.datafile = None
        self.delimiter = "comma"
        self.singleoutput = True
        self.outfilepath = None
        self.outfileDir = None
        self.outfileBase = None
        self.lineIdx = None
        self.coordIdx = None
        self.channelIdx = []
        self.DTMIdx = None
        self.loopheightIdx = None
        self.magIdx = None
        self.hiliteColour = "red"
        self.lineColour = "black"
        self.titleBase = None
        self.yLab = None
        self.xLab = None
        self.plotDTM = False
        self.plotLoopheight = False
        self.plotMag= False
        self.heightfromAltimeter = False
        self.hiliteCh = True
        self.hiliteNCh = 5
        
        #data containers
        self.easting=None
        self.amplitudes = None
        self.DTM = None
        self.mag = None
        self.loopHeight = None
        self.currentline= None
        self.readingMax = None
        self.dtmMax = None
        self.magMax = None
        self.loopMax = None
        self.lineList = []
        
        
    def run(self):
        
        if self.singleoutput:
            self.savefile = PdfPages(self.outfilepath)
            
        self.findMax()
        self.profilesStarted.emit()
        
        linecount = 0
        with open(self.datafile, "r") as csvfile:
            next(csvfile)
            if self.delimiter == "comma":
                csvreader = csv.reader(csvfile)
            elif self.delimiter == "space":
                csvreader = csv.reader(csvfile, delimiter=" ", skipinitialspace=True)
            firstdata = csvreader.next()
            #get the first Line number
            self.currentline = firstdata[self.lineIdx]
            #setup arrays
            self.makeArrays(firstdata)
                       
            for row in csvreader:
            
                if self.plotLoopheight:
                    if self.heightfromAltimeter:
                        if not self.plotDTM:
                            self.plotLoopheight = False
                            
                line = row[self.lineIdx]
                #print row[0]
                #rint float(row[0])
                #return
                if line == self.currentline:
                    self.easting = np.append(self.easting, [float(row[self.coordIdx])])
                    #get the requested channel data using list comprehension
                    channels = self.convertChannels([row[i] for i in self.channelIdx])
                    self.amplitudes = np.append(self.amplitudes, channels, axis=1)
                    
                    #populate optional profiles if requested
                    if self.plotDTM:
                        self.DTM = np.append(self.DTM, [float(row[self.DTMIdx])])
                    if self.plotLoopheight:
                        if self.heightfromAltimeter:
                            height = (float(row[self.loopheightIdx])) + (float(row[self.DTMIdx]))
                            self.loopHeight = np.append(self.loopHeight, [height])
                        else:
                            self.loopHeight = np.append(self.loopHeight, [float(row[self.loopheightIdx])])
                    if self.plotMag:
                        self.mag = np.append(self.mag, [float(row[self.magIdx])])
                else:
                    self.plotProfiles()
                    self.currentline = row[self.lineIdx]
                    self.makeArrays(row)
                    linecount += 1
                    self.profileCompleted.emit(linecount)
            #plot the last graph
            self.plotProfiles()
            linecount += 1
            self.profileCompleted.emit(linecount)
            
        if self.singleoutput:
            self.savefile.close()
            #open pdf with default appplication
            if sys.platform.startswith('darwin'):
                subprocess.call(('open', self.outfilepath))
            elif os.name == 'nt':
                os.startfile(self.outfilepath)
            elif os.name == 'posix':
                subprocess.call(('xdg-open', self.outfilepath))
        
    def makeArrays(self, row):
        self.easting = np.array([float(row[self.coordIdx])])
        #get the requested channel data using list comprehension
        channellist =[row[i] for i in self.channelIdx]
        channellistF = self.convertChannels(channellist)
        self.amplitudes = np.array(channellistF)
        
        #setup DTM data if requested
        if self.plotDTM:
            self.DTM = np.array([float(row[self.DTMIdx])])
        #setup loop height data if requested
        if self.plotLoopheight:
            self.loopHeight = np.array([float(row[self.loopheightIdx])])
        #setup DTM data if requested
        if self.plotMag:
            self.mag = np.array([float(row[self.magIdx])])
        
    def convertChannels(self, channelList):
        #convert the string list of channels into a list of list of floats
        listF=[]
        try:
            for ch in channelList:
                listF.append([float(ch)])
            return listF
        except ValueError:
            print "ch value", ch
            return
        
    def plotProfiles(self):
        #set up figure
        plot.clf()
        plot.figure(figsize=(16.5, 11.7))
        #set up main plot
        plot.subplots_adjust(left=0.0, hspace=0.3)
        ax1 = plot.subplot2grid((12,16), (0,0), rowspan=8, colspan=15)
        title = '{} Line {}'.format(self.titleBase, self.currentline)
        plot.title(title)
        plot.yscale('symlog', linthreshy=0.1, subsy=[2,3,4,5,6,7,8,9])
        plot.autoscale(axis="x", tight=True)
        ylimit = 10**(math.ceil(math.log10(self.readingMax)))
        plot.ylim(ymax=ylimit)
        plot.xlabel(self.xLab)
        plot.ylabel(self.yLab)
        #plot channel lines
        i=0
        if self.hiliteCh:
            for n in self.amplitudes:
                if i%self.hiliteNCh ==0:
                    plot.plot(self.easting, n, linewidth=0.1, color=self.hiliteColour)
                else:
                    plot.plot(self.easting, n, linewidth=0.1, color=self.lineColour)
                i+= 1
        else:
            for n in self.amplitudes:
                plot.plot(self.easting, n, linewidth=0.1, color=self.lineColour)
                i+= 1
                
        box = ax1.get_position()
        ax1.set_position([box.x0, box.y0, box.width * 0.97, box.height])

        #set up secondary plot
        ax2 = plot.subplot2grid((12,16), (9,0), rowspan=4, colspan=15)
        plot.autoscale(axis="x", tight=True)
        box = ax2.get_position()
        ax2.set_position([box.x0, box.y0, box.width * 0.97, box.height])
        if self.plotDTM:
            plot.plot(self.easting, self.DTM, label="DTM", color="black")
            lim = self.dtmMax +100
            plot.ylim(ymax=lim)
            plot.ylabel("Elevation")
        if self.plotLoopheight:
            plot.plot(self.easting, self.loopHeight, label="Loop", color="blue")
            lim = self.loopMax + 50
            plot.ylim(ymax=lim)
            plot.ylabel("Elevation")
        if self.plotMag and (self.plotDTM or self.plotLoopheight):
            ax3 = ax2.twinx()
            ax3.set_position([box.x0, box.y0, box.width * 0.97, box.height])
            ax3.plot(self.easting, self.mag, label="Magnetics", color="red")
            ax3.autoscale(axis="x", tight=True)
            ax3.set_ylabel("Magnetics")
            ax3.set_ylim(top=self.magMax)
        if self.plotMag and not (self.plotDTM or self.plotLoopheight):
            plot.plot(self.easting, self.mag, label="Magnetics", color="red")
            plot.ylim(ymax=self.magMax)
            plot.ylabel("Magnetics")
            

        ax2.legend(loc="lower left", bbox_to_anchor=(1.05,1), frameon=False, fontsize=9)
        ax3.legend(loc="lower left", bbox_to_anchor=(1.05,0.94), frameon=False, fontsize=9)
        #add text to figure
        plot.figtext(0.83,0.85, "System: VTEM \nSurvey By: Geotech Airborne\nDate: March 2009\nLocation: Koppany", size=7)
        
        if self.singleoutput:
            #save to single pdf
            self.savefile.savefig(bbox_inches="tight", pad_inches=0.5, )
        else:
            #save to individual pdfs
            savepath = os.path.normpath(r"{}{} Line {}.pdf".format(self.outfileDir, self.outfileBase, self.currentline))
            plot.savefig(savepath, bbox_inches="tight", pad_inches=0.5)
        
    def findMax(self):
        self.lineList=[]
        with open(self.datafile, "r") as csvfile:
            next(csvfile)
            if self.delimiter == "comma":
                csvreader = csv.reader(csvfile)
            elif self.delimiter == "space":
                csvreader = csv.reader(csvfile, delimiter=" ", skipinitialspace=True)
            for row in csvreader:
                #print row
            
                channels = self.convertChannels([row[i] for i in self.channelIdx])
                val = max(channels)[0]
                if val > self.readingMax:
                    self.readingMax = val
                if self.plotDTM:
                    dtmVal = float(row[self.DTMIdx])
                    if dtmVal > self.dtmMax:
                        self.dtmMax = dtmVal
                if self.plotMag:
                    magVal = float(row[self.magIdx])
                    if magVal > self.magMax:
                        self.magMax = magVal
                if self.plotLoopheight:
                    lphVal = float(row[self.loopheightIdx])
                    if lphVal > self.loopMax:
                        self.loopMax = lphVal
                        
                #make a list of unique line ids
                
                try:
                    self.lineList.index(row[self.lineIdx])
                except ValueError:
                    self.lineList.append(row[self.lineIdx])
                    
                    
            csvfile.close()
            self.numberofLines.emit(len(self.lineList))
            
    def resetParameters(self):
    #resets the parameters that are involved with plotting, to allow for fresh start.
    #does not include input file parameters and output style
        self.outfilepath = None
        self.outfileDir = None
        self.outfileBase = None
        self.lineIdx = None
        self.coordIdx = None
        self.channelIdx = []
        self.DTMIdx = None
        self.loopheightIdx = None
        self.magIdx = None
        self.hiliteColour = "red"
        self.lineColour = "black"
        self.titleBase = None
        self.yLab = None
        self.xLab = None
        self.plotDTM = False
        self.plotLoopheight = False
        self.plotMag= False
        self.heightfromAltimeter = False
        self.hiliteCh = True
        self.hiliteNCh = 5
        
        #data containers
        self.easting=None
        self.amplitudes = None
        self.DTM = None
        self.mag = None
        self.loopHeight = None
        self.currentline= None
        self.readingMax = None
        self.dtmMax = None
        self.magMax = None
        self.loopMax = None
        self.lineList = []

