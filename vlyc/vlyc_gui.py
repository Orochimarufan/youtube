# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'vlyc_gui.ui'
#
# Created: Mon Jun 11 18:44:11 2012
#      by: PyQt4 UI code generator 4.8.6
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(707, 505)
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "VideoLan Youtube Client", None, QtGui.QApplication.UnicodeUTF8))
        self.layout_root = QtGui.QWidget(MainWindow)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.layout_root.sizePolicy().hasHeightForWidth())
        self.layout_root.setSizePolicy(sizePolicy)
        self.layout_root.setSizeIncrement(QtCore.QSize(100, 100))
        self.layout_root.setObjectName(_fromUtf8("layout_root"))
        self.verticalLayout = QtGui.QVBoxLayout(self.layout_root)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.layout_main = QtGui.QVBoxLayout()
        self.layout_main.setSpacing(1)
        self.layout_main.setSizeConstraint(QtGui.QLayout.SetNoConstraint)
        self.layout_main.setObjectName(_fromUtf8("layout_main"))
        self.frame_video = QtGui.QFrame(self.layout_root)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_video.sizePolicy().hasHeightForWidth())
        self.frame_video.setSizePolicy(sizePolicy)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.AlternateBase, brush)
        self.frame_video.setPalette(palette)
        self.frame_video.setAutoFillBackground(True)
        self.frame_video.setFrameShape(QtGui.QFrame.StyledPanel)
        self.frame_video.setFrameShadow(QtGui.QFrame.Raised)
        self.frame_video.setObjectName(_fromUtf8("frame_video"))
        self.layout_main.addWidget(self.frame_video)
        self.layout_time = QtGui.QHBoxLayout()
        self.layout_time.setObjectName(_fromUtf8("layout_time"))
        self.slider_seek = QtGui.QSlider(self.layout_root)
        self.slider_seek.setOrientation(QtCore.Qt.Horizontal)
        self.slider_seek.setObjectName(_fromUtf8("slider_seek"))
        self.layout_time.addWidget(self.slider_seek)
        self.label_time = QtGui.QLabel(self.layout_root)
        self.label_time.setMinimumSize(QtCore.QSize(120, 0))
        self.label_time.setText(QtGui.QApplication.translate("MainWindow", "00:00:00/00:00:00", None, QtGui.QApplication.UnicodeUTF8))
        self.label_time.setObjectName(_fromUtf8("label_time"))
        self.layout_time.addWidget(self.label_time)
        self.layout_main.addLayout(self.layout_time)
        self.layout_controls = QtGui.QHBoxLayout()
        self.layout_controls.setObjectName(_fromUtf8("layout_controls"))
        self.button_playpause = QtGui.QPushButton(self.layout_root)
        self.button_playpause.setText(QtGui.QApplication.translate("MainWindow", "Play", None, QtGui.QApplication.UnicodeUTF8))
        self.button_playpause.setObjectName(_fromUtf8("button_playpause"))
        self.layout_controls.addWidget(self.button_playpause)
        self.button_stop = QtGui.QPushButton(self.layout_root)
        self.button_stop.setText(QtGui.QApplication.translate("MainWindow", "Stop", None, QtGui.QApplication.UnicodeUTF8))
        self.button_stop.setObjectName(_fromUtf8("button_stop"))
        self.layout_controls.addWidget(self.button_stop)
        self.qlabel_quality = QtGui.QLabel(self.layout_root)
        self.qlabel_quality.setText(QtGui.QApplication.translate("MainWindow", "Quality", None, QtGui.QApplication.UnicodeUTF8))
        self.qlabel_quality.setObjectName(_fromUtf8("qlabel_quality"))
        self.layout_controls.addWidget(self.qlabel_quality)
        self.combo_quality = QtGui.QComboBox(self.layout_root)
        self.combo_quality.setObjectName(_fromUtf8("combo_quality"))
        self.layout_controls.addWidget(self.combo_quality)
        self.qlabel_subtitles = QtGui.QLabel(self.layout_root)
        self.qlabel_subtitles.setText(QtGui.QApplication.translate("MainWindow", "Subtitles", None, QtGui.QApplication.UnicodeUTF8))
        self.qlabel_subtitles.setObjectName(_fromUtf8("qlabel_subtitles"))
        self.layout_controls.addWidget(self.qlabel_subtitles)
        self.combo_sub = QtGui.QComboBox(self.layout_root)
        self.combo_sub.setObjectName(_fromUtf8("combo_sub"))
        self.layout_controls.addWidget(self.combo_sub)
        self.slider_vol = QtGui.QSlider(self.layout_root)
        self.slider_vol.setOrientation(QtCore.Qt.Horizontal)
        self.slider_vol.setObjectName(_fromUtf8("slider_vol"))
        self.layout_controls.addWidget(self.slider_vol)
        self.button_fullscreen = QtGui.QPushButton(self.layout_root)
        self.button_fullscreen.setText(QtGui.QApplication.translate("MainWindow", "Fullscreen", None, QtGui.QApplication.UnicodeUTF8))
        self.button_fullscreen.setObjectName(_fromUtf8("button_fullscreen"))
        self.layout_controls.addWidget(self.button_fullscreen)
        self.layout_main.addLayout(self.layout_controls)
        self.verticalLayout.addLayout(self.layout_main)
        MainWindow.setCentralWidget(self.layout_root)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 707, 25))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        self.menu_file = QtGui.QMenu(self.menubar)
        self.menu_file.setTitle(QtGui.QApplication.translate("MainWindow", "File", None, QtGui.QApplication.UnicodeUTF8))
        self.menu_file.setObjectName(_fromUtf8("menu_file"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)
        self.action_quit = QtGui.QAction(MainWindow)
        self.action_quit.setText(QtGui.QApplication.translate("MainWindow", "&Quit", None, QtGui.QApplication.UnicodeUTF8))
        self.action_quit.setShortcutContext(QtCore.Qt.WindowShortcut)
        self.action_quit.setObjectName(_fromUtf8("action_quit"))
        self.action_youtubeurl = QtGui.QAction(MainWindow)
        self.action_youtubeurl.setText(QtGui.QApplication.translate("MainWindow", "&Open URL", None, QtGui.QApplication.UnicodeUTF8))
        self.action_youtubeurl.setObjectName(_fromUtf8("action_youtubeurl"))
        self.action_open = QtGui.QAction(MainWindow)
        self.action_open.setText(QtGui.QApplication.translate("MainWindow", "Open MRL", None, QtGui.QApplication.UnicodeUTF8))
        self.action_open.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+N", None, QtGui.QApplication.UnicodeUTF8))
        self.action_open.setObjectName(_fromUtf8("action_open"))
        self.action_open_file = QtGui.QAction(MainWindow)
        self.action_open_file.setText(QtGui.QApplication.translate("MainWindow", "Open File", None, QtGui.QApplication.UnicodeUTF8))
        self.action_open_file.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+O", None, QtGui.QApplication.UnicodeUTF8))
        self.action_open_file.setObjectName(_fromUtf8("action_open_file"))
        self.action_open_youtube = QtGui.QAction(MainWindow)
        self.action_open_youtube.setText(QtGui.QApplication.translate("MainWindow", "Open Youtube URL", None, QtGui.QApplication.UnicodeUTF8))
        self.action_open_youtube.setShortcut(QtGui.QApplication.translate("MainWindow", "Ctrl+Y", None, QtGui.QApplication.UnicodeUTF8))
        self.action_open_youtube.setObjectName(_fromUtf8("action_open_youtube"))
        self.menu_file.addAction(self.action_open_file)
        self.menu_file.addAction(self.action_open_youtube)
        self.menu_file.addAction(self.action_open)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_quit)
        self.menubar.addAction(self.menu_file.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        pass

