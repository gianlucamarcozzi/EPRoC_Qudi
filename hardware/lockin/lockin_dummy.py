import time
import numpy as np
import os
import subprocess

from core.module import Base
from core.configoption import ConfigOption
from interface.test_lockin_interface import LockinInterface


class LockinDummy(Base, LockinInterface):
    """
    Example config for copy-paste:

    lockin_anfatec_203:
        module.Class: 'lockin.test_lockin_anfatec_203.lockin_anfatec_203'
        gpib_address: '192.168.1.7'
    """
    tau_values = [0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50,
                  100, 200, 500, 1000]

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        return

    def on_deactivate(self):
        return

    def get_actual_value(self, param):
        """
        get the value of a parameter from Lockin.ini

        :param param: str {Amplitude|Frequency|Timeconstant|Rolloff|InputRange|Phase|Harmonic|AmplCaretPos|
                            FreqCaretPos|FreqCaretPosTail|PhaseCaretPos|DisplayChannel|Channel1Type|Channel1Range|
                            Channel2Type|Channel2Range|Channel3Type|Channel3Range|Channel4Type|Channel4Range|
                            InputCouple|InputMode|RefInFlag|TimeConstLoL|RollOffLoL|SyncLoL|Sync0|Phase0}
        :return: str parameter value
        """
        return '1'

    def set_input_range(self, r):
        """
        :param r: str {'0.1'|'1'|'10'}
                        '0.1': low noise
                        '1': normal
                        '10': high dyn. reserve
        """
        return r

    def set_coupling_type(self, coupl):
        """
        :param coupl: int {0|1}:
                        0: dc coupled
                        1: ac coupled
        :return actual_coupl:
        """
        return coupl

    def set_time_constants(self, tauA=None, tau1=None):
        """

        :param: tauA 0.1ms is not supported, tau1 {...|-10} -10: same value as tauA
        :return:
        """
        return tauA, tau1

    def set_sync_filter_settings(self, val):
        """
        manual is not really clear about this
        :param val: 0: off, 1: on
        :return:
        """
        return val, val

    def set_rolloff(self, dB):
        """
        RollOff and RollOffLoL change together with this command
        :param dB: dB/oct {6|12|24}
        :return:
        """
        return dB

    def set_input_config(self, i):
        """
        :param i: 0: A, 1: A-B, 2: A&B
        :return:
        """
        return i

    def set_amplitude(self, uac):
        return uac

    def set_frequency(self, f):
        """
        set frequency
        :param f: f
        :return: act_f
        """
        return f

    def set_phases(self, phase=None, phase0=None):
        return phase, phase0

    def set_harmonic(self, i):
        return i

    def change_reference(self, ref):
        """
        change reference signal
        :param ref: str {0|1}:
                         '0': internal reference
                         '1': external reference
        :return actual_ref: int {0|1}:
                         0: internal
                         1: external
        """
        return ref

    def get_data_lia(self):
        return [0, 0, 0, 0]

