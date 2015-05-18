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
import textwrap
import logging

from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtCore import QObject
from PyQt4.QtCore import Qt
#sys.excepthook = sys.__excepthook__
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'EMProfiler_dialog_base.ui'))
LOGFILE = os.path.join(os.path.dirname(__file__), "eventlog.txt")
logging.basicConfig(filename = LOGFILE, level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')



class EMProfilerDialog(QtGui.QDialog, FORM_CLASS):

    
    sendData =QtCore.pyqtSignal(list)
    startPlotting = QtCore.pyqtSignal()
    resetParameters = QtCore.pyqtSignal()
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
        #inititate threading
        self.workerthread = QtCore.QThread()
        #initiate profiler
        self.profiler = ProfileMaker()
        #move profiler to threading
        self.profiler.moveToThread(self.workerthread)
        #connect up signals/slots
        self.sendData.connect(self.profiler.setVariables)
        self.resetParameters.connect(self.profiler.resetParameters)
        self.startPlotting.connect(self.profiler.run)
        #self.sendData.connect(self.printSignal)
        self.workerthread.start()
        
        
        #set default parameters, populate settings combo boxes
        self.sbxHilite.setValue(5)
        self.cbxHicol.addItems(['black', 'blue', 'cyan', 'green', 'magenta', 'red', 'yellow'])
        self.cbxHicol.setCurrentIndex(5)
        self.cbxLinecol.addItems(['black', 'blue', 'cyan', 'green', 'magenta', 'red', 'yellow'])
        self.cbxLinecol.setCurrentIndex(0)
        self.plainTextEdit.setPlainText("System:\nSurvey By:\nDate:\nLocation:\nComment:")
        
        #link up buttons
        self.btnInpBrow.clicked.connect(self.showFileBrowser)
        self.btnOutfilebrow.clicked.connect(lambda: self.showSaveFile("Single"))
        self.btnOutdirbrow.clicked.connect(lambda: self.showSaveFile("Multi"))
        self.btnLoadInfo.clicked.connect(self.loadInfo)
        self.btnAddCh.clicked.connect(self.addChannels)
        self.btnRemCh.clicked.connect(self.remChannels)
        self.btnCreateProf.clicked.connect(self.makeProfiles)
        
        #Connect GUI elements with profiler parameters
        self.ledInput.textChanged.connect(lambda:self.sendData.emit(["datafile",self.ledInput.text()]))
        self.ledInput.textChanged.connect(lambda:self.setVars(["datafile",self.ledInput.text()]))
        self.ledOutfile.textChanged.connect(lambda:self.sendData.emit(["outfilepath",self.ledOutfile.text()]))
        self.ledOutdir.textChanged.connect(lambda:self.sendData.emit(["outfiledir",self.ledOutdir.text()]))
        self.ledTitle.textChanged.connect(lambda:self.sendData.emit(["titleBase",self.ledTitle.text()]))
        self.ledXlab.textChanged.connect(lambda:self.sendData.emit(["xlabel",self.ledXlab.text()]))
        self.ledYlab.textChanged.connect(lambda:self.sendData.emit(["ylabel",self.ledYlab.text()]))
        self.cbxLine.currentIndexChanged.connect(lambda:self.sendData.emit(["lineIdx",self.cbxLine.currentText()]))
        self.cbxCoord.currentIndexChanged.connect(lambda:self.sendData.emit(["coordIdx",self.cbxCoord.currentText()]))
        self.cbxDTM.currentIndexChanged.connect(lambda:self.sendData.emit(["DTMIdx",self.cbxDTM.currentText()]))
        self.cbxLoopHeight.currentIndexChanged.connect(lambda:self.sendData.emit(["loopheightIdx",self.cbxLoopHeight.currentText()]))
        self.cbxMag.currentIndexChanged.connect(lambda:self.sendData.emit(["magIdx",self.cbxMag.currentText()]))
        self.cbxHicol.currentIndexChanged.connect(lambda:self.sendData.emit(["hiliteColour",self.cbxHicol.currentText()]))
        self.cbxLinecol.currentIndexChanged.connect(lambda:self.sendData.emit(["lineColour",self.cbxLinecol.currentText()]))
        self.rbnComma.toggled.connect(lambda:self.sendData.emit(["delimiter",self.rbnComma.isChecked()]))
        self.rbnComma.toggled.connect(lambda:self.setVars(["delimiter",self.rbnComma.isChecked()]))
        self.rbnSingle.toggled.connect(lambda:self.sendData.emit(["outstyle",self.rbnSingle.isChecked()]))
        self.chkDTM.toggled.connect(lambda:self.sendData.emit(["plotDTM",self.chkDTM.isChecked()]))
        self.chkMag.toggled.connect(lambda:self.sendData.emit(["plotMag",self.chkMag.isChecked()]))
        self.chkLoopheight.toggled.connect(lambda:self.sendData.emit(["plotLoopheight",self.chkLoopheight.isChecked()]))
        self.chkHilite.toggled.connect(lambda:self.sendData.emit(["hiliteCh",self.chkHilite.isChecked()]))
        self.rbnRadar.toggled.connect(lambda:self.sendData.emit(["heightfromAltimeter",self.rbnRadar.isChecked()]))
        self.sbxHilite.valueChanged.connect(lambda:self.sendData.emit(["hilitenchan",self.sbxHilite.value()]))
        self.plainTextEdit.textChanged.connect(lambda:self.sendData.emit(["commentstring",self.plainTextEdit.toPlainText()]))
        
        #listen for signals #do these need to be modified?
        self.profiler.profilesStarted.connect(self.startProgress)
        self.profiler.profileCompleted.connect(self.updateProgress)
        self.profiler.numberofLines.connect(self.setNumberLines)
        self.profiler.runComplete.connect(self.runCompleted)
   
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
            uh = unicode(h)
            headerdict[uh]=i
            i+=1
        self.headerdict = headerdict
        self.sendData.emit(["headerdict", headerdict])  #send data to profiler
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
        
    def setVars(self, info):
        variable = info[0]
        value = info[1]
        try:
            if variable == "datafile":
                self.datafile = os.path.normpath(value)
                
            elif variable == "delimiter":
                if value:
                    self.delimiter = "comma"
                  
                else:
                    self.delimiter = "space"
                   
        except ValueError:
            pass
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
        
        #Need to convert this to a signal
        #self.profiler.resetParameters()
        #version using signal
        self.resetParameters.emit()
        
        
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
    #this may need to be modified to work over a signal
        templist = []
        for i in xrange(self.lstSelCh.count()):
            templist.append(self.lstSelCh.item(i).text())
            
        #self.profiler.channelIdx = []
        #for j in templist:
        #    self.profiler.channelIdx.append(self.headerdict[j])
        #self.profiler.channelIdx.sort()
         
        #attempt to set up via signals for multithreading
        chList = []
        for j in templist:
            chList.append(self.headerdict[j])
        chList.sort()
        self.sendData.emit(["chList", chList])
    
            
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
        self.progressBar.setMaximum(self.lineCount + 10)
        self.progressBar.setValue(10)
        self.lblProgress.setText("Plotting Profile 1 of {}".format(self.lineCount))
    def updateProgress(self, progressCount, etime):
        self.progressBar.setValue(progressCount +10)
        self.lblProgress.setText("Plotting Profile {} of {}".format(progressCount, self.lineCount))
        remtime = (etime * (self.lineCount - progressCount)) /1000
        self.lblRemtime.setText("est:{}m{}s".format(remtime//60, remtime%60))
    def runCompleted(self):
        self.btnCreateProf.setEnabled(True)
        self.lblProgress.setText("Profiles Completed")
        self.lblRemtime.setText("")
        self.pbrBusy.setMaximum(10)
        self.pbrBusy.reset()
    def makeProfiles(self):
        #run the code to generate profiles
        #self.profiler.run()
        #try creating a threading
        #procthread = myThread(self.profiler)
        #procthread.start()
        #call run by signalling to threading
        self.btnCreateProf.setEnabled(False)
        self.pbrBusy.setMaximum(0)
        self.lblProgress.setText("Finding Maximums")
        self.startPlotting.emit()
        
    def closeEvent(self, event):
        self.workerthread.exit()
        
class ProfileMaker(QObject):

    numberofLines = QtCore.pyqtSignal(int)
    profileCompleted = QtCore.pyqtSignal(int, int)
    profilesStarted = QtCore.pyqtSignal()
    runComplete = QtCore.pyqtSignal()
    
    def __init__(self):
        super(ProfileMaker, self).__init__()
        #plotting parameters
        #LOGFILE = os.path.join(os.path.dirname(__file__), "eventlog.txt")
        #logging.basicConfig(filename = LOGFILE, level=logging.INFO, format='%(asctime)s %(message)s')
        self.datafile = None
        self.delimiter = "comma"
        self.headerdict = {}
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
        self.commentstring = "System:\nSurvey By:\nDate:\nLocation:\nComment:"
        
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
        self.readerRowNumber = 0
        
    @QtCore.pyqtSlot(list)
    def setVariables(self, info):
        variable = info[0]
        value = info[1]
        logging.debug("variable recieved, {}".format(info))
        try:
            if variable == "datafile":
                self.datafile = os.path.normpath(value)
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "delimiter":
                if value:
                    self.delimiter = "comma"
                    logging.debug("variable set {}, {}".format(variable, value))
                else:
                    self.delimiter = "space"
                    logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "outstyle":
                if value:
                    self.singleoutput = True
                    logging.debug("variable set {}, {}".format(variable, value))
                else:
                    self.singleoutput = False
                    logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "outfilepath":
                self.outfilepath = os.path.normpath(value)
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "outfileDir":
                self.outfileDir = os.path.normpath(value)
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "outfilebase":
                self.outfileBase = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "lineIdx":
                logging.debug("lindIDX in setVariables triggered with {}, {}".format(variable, value))
                self.lineIdx = self.headerdict[value]
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "coordIdx":
                self.coordIdx = self.headerdict[value]
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable =="DTMIdx":
                self.DTMIdx = self.headerdict[value]
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "loopheightIdx":
                self.loopheightIdx = self.headerdict[value]
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "magIdx":
                self.magIdx = self.headerdict[value]
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "hiliteColour":
                self.hiliteColour = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "lineColour":
                self.lineColour = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "titleBase":
                self.titleBase = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "ylabel":
                self.yLab = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "xlabel":
                self.xLab = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "plotDTM":
                self.plotDTM = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "plotLoopheight":
                self.plotLoopheight = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "plotMag":
                self.plotMag = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "hiliteCh":
                self.hiliteCh = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "hilitenchan":
                self.hiliteNCh = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "heightfromAltimeter":
                self.heightfromAltimeter = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "commentstring":
                self.commentstring = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "chList":
                self.channelIdx = value
                logging.debug("variable set {}, {}".format(variable, value))
            elif variable == "headerdict":
                self.headerdict = value
                logging.debug("variable set {}, {}".format(variable, value))
            else:
                logging.debug("a match for {} was not found".format(variable))
                
        except:
            logging.exception("failed attempt to set variable {} to {}".format(variable, value))
            
    @QtCore.pyqtSlot()
    def run(self):
        #print "run started"
        logging.info("run started")
        if self.singleoutput:
            self.savefile = PdfPages(self.outfilepath)
            
        self.findMax()
        #print "find max complete"
        self.profilesStarted.emit()
        
        linecount = 0
        with open(self.datafile, "r") as csvfile:
            next(csvfile)
            if self.delimiter == "comma":
                csvreader = csv.reader(csvfile)
            elif self.delimiter == "space":
                csvreader = csv.reader(csvfile, delimiter=" ", skipinitialspace=True)
            self.readerRowNumber = 0
            firstdata = csvreader.next()
            self.readerRowNumber +=1
            #get the first Line number
            self.currentline = firstdata[self.lineIdx]
            #setup arrays
            self.makeArrays(firstdata)
            try:           
                for row in csvreader:
                    timer = QtCore.QElapsedTimer()
                    timer.start()
                    self.readerRowNumber += 1
                    if self.plotLoopheight:
                        if self.heightfromAltimeter:
                            if not self.plotDTM:
                                self.plotLoopheight = False
                                
                    line = row[self.lineIdx]
                    #print row[0]
                    #rint float(row[0])
                    #return
                    if line == self.currentline:
                        #if there is no location data then a row cannot be used
                        try:
                            self.easting = np.append(self.easting, [float(row[self.coordIdx])])
                        except ValueError:
                            #if fails due to blank data ADD LOGGING
                            logging.warning("null location value, line {}".format(self.readerRowNumber))
                            continue
                        #get the requested channel data using list comprehension
                        channels = self.convertChannels([row[i] for i in self.channelIdx])
                        #logging.debug("channel list for appending {}".format(channels))
                        self.amplitudes = np.append(self.amplitudes, channels, axis=1)
                        
                        #populate optional profiles if requested
                        if self.plotDTM:
                            try:
                                self.DTM = np.append(self.DTM, [float(row[self.DTMIdx])])
                            except ValueError:  
                                #if fails due to blank data, set to 0 ADD LOGGING
                                logging.warning("blank DTM value in row {}. Set to 0".format(self.readerRowNumber))
                                self.DTM = np.append(self.DTM, [0])
                        if self.plotLoopheight:
                            if self.heightfromAltimeter:
                                try:
                                    height = (float(row[self.loopheightIdx])) + (float(row[self.DTMIdx]))
                                    self.loopHeight = np.append(self.loopHeight, [height])
                                except ValueError:
                                    #if fails due to blank data, set to 0 ADD LOGGING
                                    self.loopHeight = np.append(self.loopHeight, [0])
                                    logging.warning("blank loopheight value in row {}. Set to 0. Check DTM and Altimeter".format(self.readerRowNumber))
                            else:
                                try:
                                    self.loopHeight = np.append(self.loopHeight, [float(row[self.loopheightIdx])])
                                except ValueError:
                                #if fails due to blank data, set to 0 ADD LOGGING
                                    self.loopHeight = np.append(self.loopHeight, [0])
                                    logging.warning("blank loop heightvalue in row {}. Set to 0".format(self.readerRowNumber))
                        if self.plotMag:
                            try:
                                self.mag = np.append(self.mag, [float(row[self.magIdx])])
                            except ValueError:
                                #if fails due to blank, give an arbitrary low number   ADD LOGGING
                                self.mag = np.append(self.mag, [self.magMax/1.5])
                                logging.warning("blank magnetic value in row {}. Set to 0".format(self.readerRowNumber))
                    else:
                        try:
                            #test if currentline can make valid array
                            test = float(row[self.coordIdx])
                            canContinue = True
                        except ValueError:
                            canContinue = False
                            logging.warning("null location value, line {}".format(self.readerRowNumber))
                        if not canContinue:
                            
                            continue
                            logging.debug("makeArrays would fail skipped plotting profiles. currentline = {}".format(self.currentline))
                            #bypass plotting and updating line if new array is unsuccessful due to
                            #blank coords
                        self.plotProfiles()
                        self.makeArrays(row)
                        self.currentline = row[self.lineIdx]
                        
                            
                        linecount += 1
                        etime = timer.restart()
                        self.profileCompleted.emit(linecount, etime)
            except:
                logging.exception("run loop failed")
            #plot the last graph
            self.plotProfiles()
            linecount += 1
            
            self.profileCompleted.emit(linecount, 0)
            
        if self.singleoutput:
            self.savefile.close()
            #open pdf with default appplication
            if sys.platform.startswith('darwin'):
                subprocess.call(('open', self.outfilepath))
            elif os.name == 'nt':
                os.startfile(self.outfilepath)
            elif os.name == 'posix':
                subprocess.call(('xdg-open', self.outfilepath))
        logging.info("run completed, {} profiles generated".format(linecount))
        self.runComplete.emit()
        
    def makeArrays(self, row):
        try:
            self.easting = np.array([float(row[self.coordIdx])])
        except ValueError:
            logging.debug("makeArrays location array failed")
            logging.warning("null location value, line {}".format(self.readerRowNumber))
            return
        #get the requested channel data using list comprehension Blank errors handled in convert channels
        channellist =[row[i] for i in self.channelIdx]
        channellistF = self.convertChannels(channellist)
        self.amplitudes = np.array(channellistF)
        
        #setup DTM data if requested
        if self.plotDTM:
            try:
                self.DTM = np.array([float(row[self.DTMIdx])])
            except ValueError:
                self.DTM = np.array([0])
                logging.warning("blank DTM value in row {}. Set to 0".format(self.readerRowNumber))
        #setup loop height data if requested
        if self.plotLoopheight:
                          
            if self.heightfromAltimeter:
                try:
                    height = (float(row[self.loopheightIdx])) + (float(row[self.DTMIdx]))
                    self.loopHeight = np.array([height])
                except ValueError:
                    #if fails due to blank data, set to 0 ADD LOGGING
                    logging.warning("blank loopheight value in row {}. Set to 0. Check DTM and Altimeter".format(self.readerRowNumber))
                    self.loopHeight = np.array([0])
            else:
                try:
                    self.loopHeight = np.array([float(row[self.loopheightIdx])])
                except ValueError:
                #if fails due to blank data, set to 0 ADD LOGGING
                    logging.warning("blank loop heightvalue in row {}. Set to 0".format(self.readerRowNumber))
                    self.loopHeight = np.array([0])
        #setup magnetic data if requested
        if self.plotMag:
            try:
                self.mag = np.array([float(row[self.magIdx])])
            except value:
                self.mag = np.array([self.magMax/1.5])
                logging.warning("blank magnetic value in row {}. Set to 0".format(self.readerRowNumber))
        return True
        
    def convertChannels(self, channelList):
        #convert the string list of channels into a list of list of floats
        #print channelList
        listF=[]
        try:
            for ch in channelList:
                try:
                    listF.append([float(ch)])
                except ValueError:
                    #convert null into arbitrary negative value
                    listF.append([-0.05])
                    logging.warning("blank channel value in row {}. Set to -0.05".format(self.readerRowNumber))
                    #add in some info logging here!!!!
            return listF
        except ValueError:
        #this outer level of error catching may now be redundant
            print "ch value", ch
            return
        
    def plotProfiles(self):
        #print "plot started"
        #set up figure
        #logging.debug("plotting line {}. data first rows {}".format(self.currentline, self.easting[1:50]))
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
        xlabel = "{}".format(self.xLab)
        ylabel = "{}".format(self.yLab)
        plot.xlabel(xlabel)
        plot.ylabel(ylabel)
        #plot channel lines
        #print "plotting lines"
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
        #print "main plot finished"
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
            #lim = self.loopMax + 50
            #plot.ylim(ymax=lim)
            plot.ylabel("Elevation")
        if self.plotMag and (self.plotDTM or self.plotLoopheight):
            ax3 = ax2.twinx()
            ax3.set_position([box.x0, box.y0, box.width * 0.97, box.height])
            ax3.plot(self.easting, self.mag, label="Magnetics", color="red")
            ax3.autoscale(axis="x", tight=True)
            ax3.set_ylabel("Magnetics")
            ax3.set_ylim(top=self.magMax)
            ax3.legend(loc="lower left", bbox_to_anchor=(1.05,0.94), frameon=False, fontsize=9)
        if self.plotMag and not (self.plotDTM or self.plotLoopheight):
            plot.plot(self.easting, self.mag, label="Magnetics", color="red")
            plot.ylim(ymax=self.magMax)
            plot.ylabel("Magnetics")
            
        #print "plotting legend"
        ax2.legend(loc="lower left", bbox_to_anchor=(1.05,1), frameon=False, fontsize=9)
        
        #add text to figure
        splitstring = self.commentstring.splitlines()
        newstring = []
        for n in splitstring:
            a = textwrap.wrap(n,30)
            newstring.extend(a)
        ctext = "\n".join(newstring)
        plot.figtext(0.83,0.85, ctext, size=7)
        #plot.figtext(0.83,0.85, "System: VTEM \nSurvey By: Geotech Airborne\nDate: March 2009\nLocation: Koppany", size=7)
        
        if self.singleoutput:
            #save to single pdf
            self.savefile.savefig(bbox_inches="tight", pad_inches=0.4 )
        else:
            #save to individual pdfs
            savepath = os.path.normpath(r"{}{} Line {}.pdf".format(self.outfileDir, self.outfileBase, self.currentline))
            plot.savefig(savepath, bbox_inches="tight", pad_inches=0.4)
        
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
                    try:
                        dtmVal = float(row[self.DTMIdx])
                    except ValueError:
                        dtmVal = 0
                    if dtmVal > self.dtmMax:
                        self.dtmMax = dtmVal
                if self.plotMag:
                    try:
                        magVal = float(row[self.magIdx])
                    except ValueError:
                        magVal=0
                    if magVal > self.magMax:
                        self.magMax = magVal
                if self.plotLoopheight:
                    if self.heightfromAltimeter:
                        try:
                            lphVal = (float(row[self.loopheightIdx])) + (float(row[self.DTMIdx]))
                        except ValueError:
                            lphVal=0
                        if lphVal > self.loopMax:
                            self.loopMax = lphVal
                    else:
                        try:
                            lphVal = float(row[self.loopheightIdx])
                        except ValueError:
                            lphVal=0
                        if lphVal > self.loopMax:
                            self.loopMax = lphVal

                #make a list of unique line ids
                
                try:
                    self.lineList.index(row[self.lineIdx])
                except ValueError:
                    self.lineList.append(row[self.lineIdx])
                    
            #print "mag max", self.magMax, "dtmMax", self.dtmMax, "loop max", self.loopMax
            csvfile.close()
            self.numberofLines.emit(len(self.lineList))
            
    @QtCore.pyqtSlot()
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


