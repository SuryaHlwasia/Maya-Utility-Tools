import time

from Qt import QtWidgets, QtCore, QtGui
import pymel.core as pym
import os
from functools import partial
import logging
import Qt
from maya import OpenMayaUI as omUI
import json

logging.basicConfig()
logger = logging.getLogger('LightingManager')
logger.setLevel(logging.DEBUG)
if(Qt.__binding__=='Pyside'):
    logger.debug('Using Pyside and Shiboken')
    from shiboken import wrapInstance
    from Qt.QtCore import Signal
elif(Qt.__binding__.startswith('PyQt')):
    logger.debug('Using PyQt and Sip')
    from sip import wrapinstance as wrapInstance
    from Qt.QtCore import pyqtSignal as Signal
else:
    logger.debug('Using Pyside2 and Shiboken')
    from shiboken2 import wrapInstance
    from Qt.QtCore import Signal

def getMayaMainWindow():
    win = omUI.MQtUtil_mainWindow()
    ptr = wrapInstance(int(win),QtWidgets.QMainWindow)
    return ptr

def getDock(name = "LightingManager"):
    deleteDock(name)
    ctrl = pym.workspaceControl(name,dockToMainWindow=('right',1),label='Lighting Manager')
    qtCtrl = omUI.MQtUtil_findControl(ctrl)
    ptr = wrapInstance(int(qtCtrl),QtWidgets.QWidget)
    return ptr

def deleteDock(name="LightingManager"):
    if(pym.workspaceControl(name,query=True,exists=True)):
        pym.deleteUI(name)
class LightManager(QtWidgets.QWidget):

    lightTypes ={
        "Point Light":pym.pointLight,
        "Spot Light":pym.spotLight,
        "Directional Light":pym.directionalLight,
        "Area Light":partial(pym.shadingNode,'areaLight',asLight=True),
        "Volume Light":partial(pym.shadingNode,'volumeLight',asLight=True)



    }
    def __init__(self,dock=True):
        if(dock):
            parent = getDock()
        else:
            deleteDock()
            try:
                pym.deleteUI('LightingManager')
            except:
                logger.debug('No previous UI exists')
            parent = QtWidgets.QDialog(parent = getMayaMainWindow())
            parent.setObjectName('Lighting_Manager')
            parent.setWindowTitle('Lighting Manager')
            layout = QtWidgets.QVBoxLayout(parent)
        super(LightManager,self).__init__(parent=parent)

        self.buildUI()
        self.populate()
        self.parent().layout().addWidget(self)
        if(not dock):
            parent.show()

    def populate(self):
        while self.scrollLayout.count():
            widget = self.scrollLayout.takeAt(0).widget()
            if(widget):
                widget.setVisible(False)
                widget.deleteLater()

        for light in pym.ls(type=("areaLight","pointLight","volumeLight","directionalLight","spotLight")):
            self.addLight(light)

    def buildUI(self):
        layout = QtWidgets.QGridLayout(self)
        self.lightTypeCB = QtWidgets.QComboBox()
        for lightType in sorted(self.lightTypes):
            self.lightTypeCB.addItem(lightType)
        layout.addWidget(self.lightTypeCB,0,0,1,2)

        createBtn = QtWidgets.QPushButton('Create')
        createBtn.clicked.connect(self.createLight)
        layout.addWidget(createBtn,0,2)

        scrollWidget = QtWidgets.QWidget()
        scrollWidget.setSizePolicy(QtWidgets.QSizePolicy.Maximum,QtWidgets.QSizePolicy.Maximum)
        self.scrollLayout = QtWidgets.QVBoxLayout(scrollWidget)

        scrollArea = QtWidgets.QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(scrollWidget)

        layout.addWidget(scrollArea,1,0,1,3)

        saveBtn = QtWidgets.QPushButton("Export")
        layout.addWidget(saveBtn,2,0)
        saveBtn.clicked.connect(self.exportLights)

        importBtn = QtWidgets.QPushButton('Import')
        layout.addWidget(importBtn,2,1)
        importBtn.clicked.connect(self.importLights)

        refreshBtn = QtWidgets.QPushButton("Refresh")
        refreshBtn.clicked.connect(self.populate)
        layout.addWidget(refreshBtn,2,2)

    def exportLights(self):
        properties = {}
        for lightWidget in self.findChildren(LightWidget):
            light = lightWidget.light
            transform = light.getTransform()

            properties[str(transform)] = {
                'translate':list(transform.translate.get()),
                'rotation': list(transform.rotate.get()),
                'lightType':pym.objectType(light),
                'intensity':light.intensity.get(),
                'color':light.color.get()
            }

            directory = self.getDirectory()
            lightFile = os.path.join(directory,'lightfile_{}.json'.format(time.strftime('%m%d%H')))
            with(open(lightFile,'w') as f):
                json.dump("testing",f,indent=4)
            logger.info('Saving file to %s' %lightFile)

    def getDirectory(self):
        directory = os.path.join(pym.internalVar(userAppDir=True), 'lightManager')
        if not os.path.exists(directory):
            os.mkdir(directory)
        return directory

    def importLights(self):
        directory = self.getDirectory()
        #fileName1 = QtWidgets.QFileDialog.getOpenFileNames(self,"light Browser",directory)
        fileName="C:/Users/ADMIN/Documents/maya/lightManager/lightfile_110517.json"
        print(fileName)
        with(open(fileName,'r',encoding='utf-8') as f):
            properties = json.load(f)

        for light,info in properties.items():
            lightType = info.get('lightType')
            print(lightType)
            for lightType1 in self.lightTypes:
                print('{}light'.format(lightType1.split()[0].lower()))
                if '{}light'.format(lightType1.split()[0].lower()) == lightType.lower():
                    break
            else:
                logger.info(("Corresponding light type not found for the light"))
                continue
            light = self.createLight(lightType=lightType1)
            light.intensity.set(info.get('intensity'))

            light.color.set(info.get('color'))

            transform = light.getTransform()
            transform.translate.set(info.get('translate'))
            transform.rotate.set(info.get('rotation'))

        self.populate()


    def createLight(self, lightType = None,add=True):
        if not lightType:
            lightType = self.lightTypeCB.currentText()
        func = self.lightTypes[lightType]

        light = func()
        if add:
            self.addLight(light)
        return light


    def addLight(self,light):
        widget = LightWidget(light)
        self.scrollLayout.addWidget(widget)
        widget.onSolo.connect(self.onSolo)

    def onSolo(self,value):
        lightWidgets = self.findChildren(LightWidget)
        for widget in lightWidgets:
            if widget!=self.sender():
                widget.disableLight(value)

class LightWidget(QtWidgets.QWidget):

    onSolo = Signal(bool)
    def __init__(self,light):
        super(LightWidget, self).__init__()
        if isinstance(light,str):
            light = pym.PyNode(light)
        if isinstance(light,pym.nodetypes.Transform):
            light = light.getShape()

        self.light = light
        self.buildUI()

    def buildUI(self):
        layout = QtWidgets.QGridLayout(self)
        self.name = QtWidgets.QCheckBox(str(self.light.getTransform()))
        self.name.setChecked(self.light.visibility.get())
        self.name.toggled.connect(lambda val:self.light.getTransform().visibility.set(val))


        layout.addWidget(self.name,0,0)

        soloBtn = QtWidgets.QPushButton('Solo')
        soloBtn.setCheckable(True)
        soloBtn.toggled.connect(lambda val: self.onSolo.emit(val))
        layout.addWidget(soloBtn,0,1)

        deleteBtn = QtWidgets.QPushButton('Delete')
        deleteBtn.clicked.connect(self.deleteLight)
        deleteBtn.setMaximumWidth(50)
        layout.addWidget(deleteBtn,0,2)

        intensity = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        intensity.setMinimum(1)
        intensity.setMaximum(1000)
        intensity.setValue(self.light.intensity.get())
        intensity.valueChanged.connect(lambda val:self.light.intensity.set(val))
        layout.addWidget(intensity,1,0,1,2)

        self.colorBtn = QtWidgets.QPushButton()
        self.colorBtn.setMaximumWidth(20)
        self.colorBtn.setMaximumHeight(20)
        self.setButtonColor()
        self.colorBtn.clicked.connect(self.setColor)
        layout.addWidget(self.colorBtn,1,2)

    def setButtonColor(self,color=None):
        if not color:
            color = self.light.color.get()

        assert len(color)==3,"Colors not provided"

        r,g,b = [c*255 for c in color]

        self.colorBtn.setStyleSheet('background-color:rgba(%s, %s,%s,1.0)' %(r,g,b))


    def setColor(self):
        lightColor = self.light.color.get()
        color = pym.colorEditor(rgbValue = lightColor)
        r,g,b,a = [float(x) for x in color.split()]
        color = (r,g,b)

        self.light.color.set(color)
        self.setButtonColor(color)

    def deleteLight(self):
        self.setParent(None)
        self.setVisible(False)
        self.deleteLater()

        pym.delete(self.light.getTransform())
    def disableLight(self,value):
        self.name.setChecked(not value)

