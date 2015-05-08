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

import os

from PyQt4 import QtGui, uic

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
        
        #initialise parameters
        
        #link up buttons, set default parameters
        
        #get inout data
        
    def loadInfo(self):
        pass
        #open and read header data
        
        #populate comboboxes and lists
    def addChannels(self):
        pass
        
    def remChannels(self):
        pass
        
    def setVariables(self, target, value):
        pass
        
    def showFileBrowser(self):
    #call up a file browser with filter for extension. 
    #target is the Gui element to set text to

        self.ledDHlogs.setText(QtGui.QFileDialog.getOpenFileName(self, 'Select EM Data file', rootdir, "*.csv"))
    
    def showSaveFile(self, target):
        if target == "Single":
            self.ledOutfile.setText(QtGui.QFileDialog.getSaveFileName(self, 'Save File', "/", "*.pdf"))
        elif target == "Multi":
            self.ledOutdir.setText(QtGui.QFileDialog.getExistingDirectory(self, 'Select Project Directory', rootdir,QtGui.QFileDialog.ShowDirsOnly))
            
    def makeProfiles(self):
        #run the code to generate profiles
        pass
    
    