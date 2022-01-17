import numpy as np

from core.module import Base
from core.connector import Connector
from interface.test_lockin_interface import LockinInterface


class LockinDummy(Base, LockinInterface):
    """
    Example config for copy-paste:

    lockin_dummy:
        module.Class: 'lockin.lockin_dummy.LockinDummy'
        gpib_address: 'dummy'
    """

    # connectors
    # fitlogic = Connector(interface='FitLogic')

    tau_values = [0.0002, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50,
                  100, 200, 500, 1000]

    def on_activate(self):
        """ Initialisation performed during activation of the module. """
        # self._fit_logic = self.fitlogic()
        return

    def on_deactivate(self):
        """ Deactivation of the module. """
        self.log.debug('Lockin is shutting down.')
        return

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
        """
        :param uac: amplitude
        :return actual_uac: actual_amplitude
        """
        return uac

    def set_frequency(self, f):
        """
        set frequency
        :param f: f
        :return: act_f
        """
        return f

    def set_phases(self, phase=None, phase0=None):
        """
        :param phase: phase channel A
        :param phase0: phase channel B
        """
        return phase, phase0

    def set_harmonic(self, i):
        """
        :param: i: {1|...|15}
        """
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
        """
        random values between -1 and 1
        """
        return np.random.rand(4)*2-1

