# -*- coding: utf-8 -*-
"""
This file contains the Qudi GUI module for ODMR control.

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import os
import pyqtgraph as pg

from core.connector import Connector
from core.util import units
from gui.guibase import GUIBase
from gui.guiutils import ColorBar
from gui.colordefs import ColorScaleInferno
from gui.colordefs import QudiPalettePale as palette
from gui.fitsettings import FitSettingsDialog, FitSettingsComboBox
from qtpy import QtCore
from qtpy import QtCore, QtWidgets, uic
from qtwidgets.scientific_spinbox import ScienDSpinBox
from qtpy import uic
from functools import partial


class EPRoCMainWindow(QtWidgets.QMainWindow):
    """
    The main window for the EPRoC measurement GUI.
    """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_fieldsweep.ui')

        # Load it
        super(EPRoCMainWindow, self).__init__()
        uic.loadUi(ui_file, self)
        self.show()

class EPRoCGui(GUIBase):
    """
    This is the GUI Class for EPRoC measurements
    """

    # declare connectors
    eproclogic1 = Connector(interface='EPRoCLogic')
    savelogic = Connector(interface='SaveLogic')

    sigStartEprocScan = QtCore.Signal()
    sigStopEprocScan = QtCore.Signal()
    sigScanParamsChanged = QtCore.Signal()
    sigStartOdmrScan = QtCore.Signal()
    sigStopOdmrScan = QtCore.Signal()
    #    sigContinueOdmrScan = QtCore.Signal()
    #    sigClearData = QtCore.Signal()
    sigCwMwOn = QtCore.Signal()
    sigMwOff = QtCore.Signal()
    sigMwPowerChanged = QtCore.Signal(float)
    sigMwCwParamsChanged = QtCore.Signal(float, float)
    sigMwSweepParamsChanged = QtCore.Signal(list, list, list, float)
    #    sigClockFreqChanged = QtCore.Signal(float)
    #    sigOversamplingChanged = QtCore.Signal(int)
    #    sigLockInChanged = QtCore.Signal(bool)
    #    sigFitChanged = QtCore.Signal(str)
    #    sigNumberOfLinesChanged = QtCore.Signal(int)
    #    sigRuntimeChanged = QtCore.Signal(float)
    #    sigDoFit = QtCore.Signal(str, object, object, int, int)
    sigSaveMeasurement = QtCore.Signal(str)
    #    sigAverageLinesChanged = QtCore.Signal(int)

    sigModOn = QtCore.Signal()
    sigModOff = QtCore.Signal()
    sigFmOn = QtCore.Signal()
    sigFmOff = QtCore.Signal()
    sigExtRefOn = QtCore.Signal()
    sigExtRefOff = QtCore.Signal()
    sigFmParamsChanged = QtCore.Signal(str, float, float, str)
    sigLockinParamsChanged = QtCore.Signal(float, int, int, int, int, int, float, float, float, float, int, float)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition, configuration and initialisation of the ODMR GUI.

        This init connects all the graphic modules, which were created in the
        *.ui file and configures the event handling between the modules.
        """

        self._eproc_logic = self.odmrlogic1()

        # Use the inherited class 'Ui_EPRoCGuiUI' to create now the GUI element:
        self._mw = EPRoCMainWindow()

        # Create a QSettings object for the mainwindow and store the actual GUI layout
        self.mwsettings = QtCore.QSettings("QUDI", "ODMR")
        self.mwsettings.setValue("geometry", self._mw.saveGeometry())
        self.mwsettings.setValue("windowState", self._mw.saveState())

        # Get hardware constraints to set limits for input widgets
        constraints = self._eproc_logic.get_hw_constraints()

        # Adjust range of scientific spinboxes above what is possible in Qt Designer
        self._mw.cw_frequency_DoubleSpinBox.setMaximum(constraints.max_frequency)
        self._mw.cw_frequency_DoubleSpinBox.setMinimum(constraints.min_frequency)
        self._mw.cw_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.cw_power_DoubleSpinBox.setMinimum(constraints.min_power)
        self._mw.sweep_power_DoubleSpinBox.setMaximum(constraints.max_power)
        self._mw.sweep_power_DoubleSpinBox.setMinimum(constraints.min_power)

        # Add grid layout for ranges
        groupBox = QtWidgets.QGroupBox(self._mw.dockWidgetContents_3)
        groupBox.setAlignment(QtCore.Qt.AlignLeft)
        groupBox.setTitle('Scanning Ranges')
        gridLayout = QtWidgets.QGridLayout(groupBox)
        for row in range(self._eproc_logic.ranges):
            # start
            start_label = QtWidgets.QLabel(groupBox)
            start_label.setText('Start:')
            setattr(self._mw.odmr_control_DockWidget, 'start_label_{}'.format(row), start_label)
            start_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
            start_freq_DoubleSpinBox.setSuffix('Hz')
            start_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
            start_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
            start_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
            start_freq_DoubleSpinBox.setValue(self._eproc_logic.mw_starts[row])
            start_freq_DoubleSpinBox.setMinimumWidth(75)
            start_freq_DoubleSpinBox.setMaximumWidth(100)
            setattr(self._mw.odmr_control_DockWidget, 'start_freq_DoubleSpinBox_{}'.format(row),
                    start_freq_DoubleSpinBox)
            gridLayout.addWidget(start_label, row, 1, 1, 1)
            gridLayout.addWidget(start_freq_DoubleSpinBox, row, 2, 1, 1)
            start_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
            # step
            step_label = QtWidgets.QLabel(groupBox)
            step_label.setText('Step:')
            setattr(self._mw.odmr_control_DockWidget, 'step_label_{}'.format(row), step_label)
            step_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
            step_freq_DoubleSpinBox.setSuffix('Hz')
            step_freq_DoubleSpinBox.setMaximum(100e9)
            step_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
            step_freq_DoubleSpinBox.setValue(self._eproc_logic.mw_steps[row])
            step_freq_DoubleSpinBox.setMinimumWidth(75)
            step_freq_DoubleSpinBox.setMaximumWidth(100)
            step_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
            setattr(self._mw.odmr_control_DockWidget, 'step_freq_DoubleSpinBox_{}'.format(row),
                    step_freq_DoubleSpinBox)
            gridLayout.addWidget(step_label, row, 3, 1, 1)
            gridLayout.addWidget(step_freq_DoubleSpinBox, row, 4, 1, 1)

            # stop
            stop_label = QtWidgets.QLabel(groupBox)
            stop_label.setText('Stop:')
            setattr(self._mw.odmr_control_DockWidget, 'stop_label_{}'.format(row), stop_label)
            stop_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
            stop_freq_DoubleSpinBox.setSuffix('Hz')
            stop_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
            stop_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
            stop_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
            stop_freq_DoubleSpinBox.setValue(self._eproc_logic.mw_stops[row])
            stop_freq_DoubleSpinBox.setMinimumWidth(75)
            stop_freq_DoubleSpinBox.setMaximumWidth(100)
            stop_freq_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)
            setattr(self._mw.odmr_control_DockWidget, 'stop_freq_DoubleSpinBox_{}'.format(row),
                    stop_freq_DoubleSpinBox)
            gridLayout.addWidget(stop_label, row, 5, 1, 1)
            gridLayout.addWidget(stop_freq_DoubleSpinBox, row, 6, 1, 1)

            # on the first row add buttons to add and remove measurement ranges
            if row == 0:
                # # stop
                # stop_label = QtWidgets.QLabel(groupBox)
                # stop_label.setText('Stop:')
                # setattr(self._mw.odmr_control_DockWidget, 'stop_label_{}'.format(row), stop_label)
                # stop_freq_DoubleSpinBox = ScienDSpinBox(groupBox)
                # stop_freq_DoubleSpinBox.setMaximum(constraints.max_frequency)
                # stop_freq_DoubleSpinBox.setMinimum(constraints.min_frequency)
                # stop_freq_DoubleSpinBox.setMinimumSize(QtCore.QSize(80, 0))
                # stop_freq_DoubleSpinBox.setValue(self._eproc_logic.mw_stops[row])
                # stop_freq_DoubleSpinBox.setMinimumWidth(75)
                # stop_freq_DoubleSpinBox.setMaximumWidth(100)
                # setattr(self._mw.odmr_control_DockWidget, 'stop_freq_DoubleSpinBox_{}'.format(row),
                #         stop_freq_DoubleSpinBox)
                # add range
                add_range_button = QtWidgets.QPushButton(groupBox)
                add_range_button.setText('Add Range')
                add_range_button.setMinimumWidth(75)
                add_range_button.setMaximumWidth(100)
                if self._eproc_logic.mw_scanmode.name == 'SWEEP':
                    add_range_button.setDisabled(True)
                add_range_button.clicked.connect(self.add_ranges_gui_elements_clicked)
                gridLayout.addWidget(add_range_button, row, 7, 1, 1)
                setattr(self._mw.odmr_control_DockWidget, 'add_range_button',
                        add_range_button)

                remove_range_button = QtWidgets.QPushButton(groupBox)
                remove_range_button.setText('Remove Range')
                remove_range_button.setMinimumWidth(75)
                remove_range_button.setMaximumWidth(100)
                remove_range_button.clicked.connect(self.remove_ranges_gui_elements_clicked)
                gridLayout.addWidget(remove_range_button, row, 8, 1, 1)
                setattr(self._mw.odmr_control_DockWidget, 'remove_range_button',
                        remove_range_button)

        #                matrix_range_label = QtWidgets.QLabel(groupBox)
        #                matrix_range_label.setText('Matrix Range:')
        #                matrix_range_label.setMinimumWidth(75)
        #                matrix_range_label.setMaximumWidth(100)
        #                gridLayout.addWidget(matrix_range_label, row + 1, 7, 1, 1)

        #                matrix_range_SpinBox = QtWidgets.QSpinBox(groupBox)
        #                matrix_range_SpinBox.setValue(0)
        #                matrix_range_SpinBox.setMinimumWidth(75)
        #                matrix_range_SpinBox.setMaximumWidth(100)
        #                matrix_range_SpinBox.setMaximum(self._eproc_logic.ranges - 1)
        #                gridLayout.addWidget(matrix_range_SpinBox, row + 1, 8, 1, 1)
        #                setattr(self._mw.odmr_control_DockWidget, 'matrix_range_SpinBox',
        #                        matrix_range_SpinBox)

        #        self._mw.fit_range_SpinBox.setMaximum(self._eproc_logic.ranges - 1)
        setattr(self._mw.odmr_control_DockWidget, 'ranges_groupBox', groupBox)
        self._mw.dockWidgetContents_3_grid_layout = self._mw.dockWidgetContents_3.layout()
        #        self._mw.fit_range_SpinBox.valueChanged.connect(self.change_fit_range)
        # (QWidget * widget, int row, int column, Qt::Alignment alignment = Qt::Alignment())

        self._mw.dockWidgetContents_3_grid_layout.addWidget(groupBox, 8, 0, 1, 5)
        '''
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(500)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)


        # add a clear button to clear the ODMR plots:
        self._mw.clear_odmr_PushButton = QtWidgets.QPushButton(self._mw)
        self._mw.clear_odmr_PushButton.setText('Clear ODMR')
        self._mw.clear_odmr_PushButton.setToolTip('Clear the data of the\n'
                                                  'current ODMR measurements.')
        self._mw.clear_odmr_PushButton.setEnabled(False)
        self._mw.toolBar.addWidget(self._mw.clear_odmr_PushButton)
        '''

        # Get the image from the logic
        self.channel0_image = pg.PlotDataItem(self._eproc_logic.odmr_plot_x,
                                              self._eproc_logic.odmr_plot_y[:, 0],
                                              pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                              symbol='o',
                                              symbolPen=palette.c1,
                                              symbolBrush=palette.c1,
                                              symbolSize=7)

        self.channel1_image = pg.PlotDataItem(self._eproc_logic.odmr_plot_x,
                                              self._eproc_logic.odmr_plot_y[:, 1],
                                              pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                              symbol='o',
                                              symbolPen=palette.c1,
                                              symbolBrush=palette.c1,
                                              symbolSize=7)

        self.channel2_image = pg.PlotDataItem(self._eproc_logic.odmr_plot_x,
                                              self._eproc_logic.odmr_plot_y[:, 0],
                                              pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                              symbol='o',
                                              symbolPen=palette.c1,
                                              symbolBrush=palette.c1,
                                              symbolSize=7)

        self.channel3_image = pg.PlotDataItem(self._eproc_logic.odmr_plot_x,
                                              self._eproc_logic.odmr_plot_y[:, 1],
                                              pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                                              symbol='o',
                                              symbolPen=palette.c1,
                                              symbolBrush=palette.c1,
                                              symbolSize=7)

        # Add the display item to the xy and xz ViewWidget, which was defined in the UI file.
        self._mw.channel0_PlotWidget.addItem(self.channel0_image)
        self._mw.channel0_PlotWidget.setLabel(axis='left', text='Counts', units='Counts/s')
        self._mw.channel0_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.channel0_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.channel1_PlotWidget.addItem(self.channel1_image)
        self._mw.channel1_PlotWidget.setLabel(axis='left', text='Counts', units='Counts/s')
        self._mw.channel1_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.channel1_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.channel2_PlotWidget.addItem(self.channel2_image)
        self._mw.channel2_PlotWidget.setLabel(axis='left', text='Counts', units='Counts/s')
        self._mw.channel2_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.channel2_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        self._mw.channel3_PlotWidget.addItem(self.channel3_image)
        self._mw.channel3_PlotWidget.setLabel(axis='left', text='Counts', units='Counts/s')
        self._mw.channel3_PlotWidget.setLabel(axis='bottom', text='Frequency', units='Hz')
        self._mw.channel3_PlotWidget.showGrid(x=True, y=True, alpha=0.8)

        ########################################################################
        #          Configuration of the various display Widgets                #
        ########################################################################
        # Take the default values from logic:
        self._mw.cw_frequency_DoubleSpinBox.setValue(self._eproc_logic.cw_mw_frequency)
        self._mw.cw_power_DoubleSpinBox.setValue(self._eproc_logic.cw_mw_power)
        self._mw.sweep_power_DoubleSpinBox.setValue(self._eproc_logic.sweep_mw_power)

        # to add: a remaining time display
        self._mw.elapsed_sweeps_DisplayWidget.display(self._eproc_logic.elapsed_sweeps)

        ########################################################################
        #                       Connect signals                                #
        ########################################################################
        # Internal user input changed signals
        self._mw.cw_frequency_DoubleSpinBox.editingFinished.connect(self.change_cw_params)
        self._mw.cw_power_DoubleSpinBox.editingFinished.connect(self.change_cw_params)
        self._mw.sweep_power_DoubleSpinBox.editingFinished.connect(self.change_sweep_params)

        self._mw.lockin_range_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lockin_acdc_coupling_comboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lockin_taua_comboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lockin_taub_comboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lockin_slope_comboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lockin_config_comboBox.currentTextChanged.connect(self.change_lockin_params)
        self._mw.lockin_amplitude_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.int_ref_frequency_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lockin_phase_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.lockin_phase1_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.harmonic_spinBox.editingFinished.connect(self.change_lockin_params)
        self._mw.waiting_time_factor_DoubleSpinBox.editingFinished.connect(self.change_lockin_params)

        self._mw.external_reference_radioButton.clicked.connect(self.on_off_external_reference)

        self._mw.number_of_sweeps_spinBox.editingFinished.connect(self.change_scan_params)
        self._mw.number_of_accumulations_spinBox.editingFinished.connect(self.change_scan_params)

        self._mw.source_shape_comboBox.currentTextChanged.connect(self.change_fm_params)
        self._mw.source_frequency_DoubleSpinBox.editingFinished.connect(self.change_fm_params)
        self._mw.mod_dev_frequency_DoubleSpinBox.editingFinished.connect(self.change_fm_params)
        self._mw.mod_mode_comboBox.currentTextChanged.connect(self.change_fm_params)

        # Internal trigger signals
        self._mw.action_toggle_cw.triggered.connect(self.toggle_cw_mode)
        self._mw.action_start_stop_scan.triggered.connect(self.start_stop_scan)
        self._mw.action_Save.triggered.connect(self.save_data)

        # Control/values-changed signals to logic
        self.sigCwMwOn.connect(self._eproc_logic.mw_cw_on, QtCore.Qt.QueuedConnection)
        self.sigMwOff.connect(self._eproc_logic.mw_off, QtCore.Qt.QueuedConnection)
        self.sigStartEprocScan.connect(self._eproc_logic.start_scan, QtCore.Qt.QueuedConnection)
        self.sigStopErocScan.connect(self._eproc_logic.stop__eproc_scan, QtCore.Qt.QueuedConnection)
        self.sigExtRefOn.connect(self._eproc_logic.lockin_ext_ref_on, QtCore.Qt.QueuedConnection)
        self.sigExtRefOff.connect(self._eproc_logic.lockin_ext_ref_off, QtCore.Qt.QueuedConnection)

        self.sigMwCwParamsChanged.connect(self._eproc_logic.set_cw_parameters,
                                          QtCore.Qt.QueuedConnection)
        self.sigMwSweepParamsChanged.connect(self._eproc_logic.set_sweep_parameters,
                                             QtCore.Qt.QueuedConnection)
        self.sigLockinParamsChanged.connect(self._eproc_logic.set_lockin_parameters, QtCore.Qt.QueuedConnection)
        self.sigFmParamsChanged.connect(self._eproc_logic.set_fm_parameters, QtCore.Qt.QueuedConnection)
        self.sigScanParamsChanged.connect(self._eproc_logic.set_scan_parameters, QtCore.Qt.QueuedConnection)

        self.sigSaveMeasurement.connect(self._eproc_logic.save_eproc_data, QtCore.Qt.QueuedConnection)

        # Update signals coming from logic:
        self._eproc_logic.sigParameterUpdated.connect(self.update_parameter,
                                                     QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigOutputStateUpdated.connect(self.update_status,
                                                       QtCore.Qt.QueuedConnection)
        self._eproc_logic.sigEprocPlotsUpdated.connect(self.update_plots, QtCore.Qt.QueuedConnection)

        # Show the Main ODMR GUI:
        self.show()

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Disconnect signals
        #        self._sd.buttonBox.button(QtWidgets.QDialogButtonBox.Apply).clicked.disconnect()
        #        self._sd.accepted.disconnect()
        #        self._sd.rejected.disconnect()
        #        self._mw.action_Settings.triggered.disconnect()
        self._eproc_logic.sigParameterUpdated.disconnect()
        self._eproc_logic.sigOutputStateUpdated.disconnect()
        self._eproc_logic.sigOdmrPlotsUpdated.disconnect()
        #        self._eproc_logic.sigOdmrFitUpdated.disconnect()
        #        self._eproc_logic.sigOdmrElapsedTimeUpdated.disconnect()
        self.sigCwMwOn.disconnect()
        self.sigMwOff.disconnect()
        #        self.sigClearData.disconnect()
        self.sigStartOdmrScan.disconnect()
        self.sigStopOdmrScan.disconnect()
        #        self.sigContinueOdmrScan.disconnect()
        #        self.sigDoFit.disconnect()
        self.sigMwCwParamsChanged.disconnect()
        self.sigMwSweepParamsChanged.disconnect()
        #        self.sigRuntimeChanged.disconnect()
        #        self.sigNumberOfLinesChanged.disconnect()
        #        self.sigClockFreqChanged.disconnect()
        #        self.sigOversamplingChanged.disconnect()
        #        self.sigLockInChanged.disconnect()
        #        self.sigSaveMeasurement.disconnect()
        #        self.sigAverageLinesChanged.disconnect()
        #        self._mw.odmr_cb_manual_RadioButton.clicked.disconnect()
        #        self._mw.odmr_cb_centiles_RadioButton.clicked.disconnect()
        #        self._mw.clear_odmr_PushButton.clicked.disconnect()
        #        self._mw.action_run_stop.triggered.disconnect()
        #        self._mw.action_resume_odmr.triggered.disconnect()
        #        self._mw.action_Save.triggered.disconnect()
        self._mw.action_toggle_cw.triggered.disconnect()
        #        self._mw.action_RestoreDefault.triggered.disconnect()
        #        self._mw.do_fit_PushButton.clicked.disconnect()
        self._mw.cw_frequency_DoubleSpinBox.editingFinished.disconnect()
        dspinbox_dict = self.get_all_dspinboxes_from_groupbox()
        for identifier_name in dspinbox_dict:
            dspinbox_type_list = dspinbox_dict[identifier_name]
            [dspinbox_type.editingFinished.disconnect() for dspinbox_type in dspinbox_type_list]

        self._mw.cw_power_DoubleSpinBox.editingFinished.disconnect()
        self._mw.sweep_power_DoubleSpinBox.editingFinished.disconnect()
        #        self._mw.runtime_DoubleSpinBox.editingFinished.disconnect()
        #        self._mw.odmr_cb_max_DoubleSpinBox.valueChanged.disconnect()
        #        self._mw.odmr_cb_min_DoubleSpinBox.valueChanged.disconnect()
        #        self._mw.odmr_cb_high_percentile_DoubleSpinBox.valueChanged.disconnect()
        #        self._mw.odmr_cb_low_percentile_DoubleSpinBox.valueChanged.disconnect()
        #        self._mw.average_level_SpinBox.valueChanged.disconnect()
        #        self._fsd.sigFitsUpdated.disconnect()
        #        self._mw.fit_range_SpinBox.editingFinished.disconnect()
        #        self._mw.action_FitSettings.triggered.disconnect()
        self._mw.fm_on_off_checkBox.clicked.disconnect()
        self.sigFmOn.disconnect()
        self.sigFmOff.disconnect()
        self.sigExtRefOn.disconnect()
        self.sigExtRefOff.disconnect()
        self._mw.source_shape_comboBox.currentTextChanged.disconnect()
        self._mw.source_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.mod_dev_frequency_DoubleSpinBox.editingFinished.disconnect()
        self._mw.mod_mode_comboBox.currentTextChanged.disconnect()
        self.sigFmParamsChanged.disconnect()
        self.sigLockinParamsChanged.disconnect()
        self.sigStartScan.disconnect()
        self.sigStopScan.disconnect()
        self.sigScanParamsChanged.disconnect()
        self._mw.close()
        return 0

    def show(self):
        """Make window visible and put it above all other windows. """
        self._mw.show()
        self._mw.activateWindow()
        self._mw.raise_()
    def update_parameter(self, param_dict):
        """ Update the parameter display in the GUI.

        @param param_dict:
        @return:

        Any change event from the logic should call this update function.
        The update will block the GUI signals from emitting a change back to the
        logic.
        """
        param = param_dict.get('sweep_mw_power')
        if param is not None:
            self._mw.sweep_power_DoubleSpinBox.blockSignals(True)
            self._mw.sweep_power_DoubleSpinBox.setValue(param)
            self._mw.sweep_power_DoubleSpinBox.blockSignals(False)

        mw_starts = param_dict.get('mw_starts')
        mw_steps = param_dict.get('mw_steps')
        mw_stops = param_dict.get('mw_stops')

        if mw_starts is not None:
            start_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('start')
            for mw_start, start_frequency_box in zip(mw_starts, start_frequency_boxes):
                start_frequency_box.blockSignals(True)
                start_frequency_box.setValue(mw_start)
                start_frequency_box.blockSignals(False)

        if mw_steps is not None:
            step_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('step')
            for mw_step, step_frequency_box in zip(mw_steps, step_frequency_boxes):
                step_frequency_box.blockSignals(True)
                step_frequency_box.setValue(mw_step)
                step_frequency_box.blockSignals(False)

        if mw_stops is not None:
            stop_frequency_boxes = self.get_freq_dspinboxes_from_groubpox('stop')
            for mw_stop, stop_frequency_box in zip(mw_stops, stop_frequency_boxes):
                stop_frequency_box.blockSignals(True)
                stop_frequency_box.setValue(mw_stop)
                stop_frequency_box.blockSignals(False)

        param = param_dict.get('run_time')
        if param is not None:
            self._mw.runtime_DoubleSpinBox.blockSignals(True)
            self._mw.runtime_DoubleSpinBox.setValue(param)
            self._mw.runtime_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('number_of_lines')
        if param is not None:
            self._sd.matrix_lines_SpinBox.blockSignals(True)
            self._sd.matrix_lines_SpinBox.setValue(param)
            self._sd.matrix_lines_SpinBox.blockSignals(False)

        param = param_dict.get('clock_frequency')
        if param is not None:
            self._sd.clock_frequency_DoubleSpinBox.blockSignals(True)
            self._sd.clock_frequency_DoubleSpinBox.setValue(param)
            self._sd.clock_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('oversampling')
        if param is not None:
            self._sd.oversampling_SpinBox.blockSignals(True)
            self._sd.oversampling_SpinBox.setValue(param)
            self._sd.oversampling_SpinBox.blockSignals(False)

        param = param_dict.get('lock_in')
        if param is not None:
            self._sd.lock_in_CheckBox.blockSignals(True)
            self._sd.lock_in_CheckBox.setChecked(param)
            self._sd.lock_in_CheckBox.blockSignals(False)

        param = param_dict.get('cw_mw_frequency')
        if param is not None:
            self._mw.cw_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.cw_frequency_DoubleSpinBox.setValue(param)
            self._mw.cw_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('cw_mw_power')
        if param is not None:
            self._mw.cw_power_DoubleSpinBox.blockSignals(True)
            self._mw.cw_power_DoubleSpinBox.setValue(param)
            self._mw.cw_power_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('average_length')
        if param is not None:
            self._mw.average_level_SpinBox.blockSignals(True)
            self._mw.average_level_SpinBox.setValue(param)
            self._mw.average_level_SpinBox.blockSignals(False)

        param = param_dict.get('fm_shape')
        if param is not None:
            self._mw.source_shape_comboBox.blockSignals(True)
            self._mw.source_shape_comboBox.setCurrentText(param)
            self._mw.source_shape_comboBox.blockSignals(False)

        param = param_dict.get('fm_freq')
        if param is not None:
            self._mw.source_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.source_frequency_DoubleSpinBox.setValue(param)
            self._mw.source_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('fm_dev')
        if param is not None:
            self._mw.mod_dev_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.mod_dev_frequency_DoubleSpinBox.setValue(param)
            self._mw.mod_dev_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('fm_mode')
        if param is not None:
            self._mw.mod_mode_comboBox.blockSignals(True)
            self._mw.mod_mode_comboBox.setCurrentText(param)
            self._mw.mod_mode_comboBox.blockSignals(False)

        param = param_dict.get('lockin_range')
        if param is not None:
            self._mw.lockin_range_DoubleSpinBox.blockSignals(True)
            self._mw.lockin_range_DoubleSpinBox.setValue(param)
            self._mw.lockin_range_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('coupl')
        if param is not None:
            self._mw.lockin_acdc_coupling_comboBox.blockSignals(True)
            self._mw.lockin_acdc_coupling_comboBox.setCurrentIndex(param)
            self._mw.lockin_acdc_coupling_comboBox.blockSignals(False)

        param = param_dict.get('tauA')
        if param is not None:
            self._mw.lockin_taua_comboBox.blockSignals(True)
            self._mw.lockin_taua_comboBox.setCurrentIndex(param)
            self._mw.lockin_taua_comboBox.blockSignals(False)

        param = param_dict.get('tauB')
        if param is not None:
            if param == -10:
                param = 22
            self._mw.lockin_taub_comboBox.blockSignals(True)
            self._mw.lockin_taub_comboBox.setCurrentIndex(param)
            self._mw.lockin_taub_comboBox.blockSignals(False)

        param = param_dict.get('slope')
        if param is not None:
            self._mw.lockin_slope_comboBox.blockSignals(True)
            self._mw.lockin_slope_comboBox.setCurrentText(str(param) + 'dB/oct')
            self._mw.lockin_slope_comboBox.blockSignals(False)

        param = param_dict.get('config')
        if param is not None:
            self._mw.lockin_config_comboBox.blockSignals(True)
            self._mw.lockin_config_comboBox.setCurrentIndex(param)
            self._mw.lockin_config_comboBox.blockSignals(False)

        param = param_dict.get('amplitude')
        if param is not None:
            self._mw.lockin_amplitude_DoubleSpinBox.blockSignals(True)
            self._mw.lockin_amplitude_DoubleSpinBox.setValue(param)
            self._mw.lockin_amplitude_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('int_freq')
        if param is not None:
            self._mw.int_ref_frequency_DoubleSpinBox.blockSignals(True)
            self._mw.int_ref_frequency_DoubleSpinBox.setValue(param)
            self._mw.int_ref_frequency_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('phase')
        if param is not None:
            self._mw.lockin_phase_DoubleSpinBox.blockSignals(True)
            self._mw.lockin_phase_DoubleSpinBox.setValue(param)
            self._mw.lockin_phase_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('phase1')
        if param is not None:
            self._mw.lockin_phase1_DoubleSpinBox.blockSignals(True)
            self._mw.lockin_phase1_DoubleSpinBox.setValue(param)
            self._mw.lockin_phase1_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('harmonic')
        if param is not None:
            self._mw.harmonic_spinBox.blockSignals(True)
            self._mw.harmonic_spinBox.setValue(param)
            self._mw.harmonic_spinBox.blockSignals(False)

        param = param_dict.get('waiting_time_factor')
        if param is not None:
            self._mw.waiting_time_factor_DoubleSpinBox.blockSignals(True)
            self._mw.waiting_time_factor_DoubleSpinBox.setValue(param)
            self._mw.waiting_time_factor_DoubleSpinBox.blockSignals(False)

        param = param_dict.get('number_of_sweeps')
        if param is not None:
            self._mw.number_of_sweeps_spinBox.blockSignals(True)
            self._mw.number_of_sweeps_spinBox.setValue(param)
            self._mw.number_of_sweeps_spinBox.blockSignals(False)

        param = param_dict.get('number_of_accumulations')
        if param is not None:
            self._mw.number_of_accumulations_spinBox.blockSignals(True)
            self._mw.number_of_accumulations_spinBox.setValue(param)
            self._mw.number_of_accumulations_spinBox.blockSignals(False)
        return
