from struct import pack, unpack
import serial
import time
from core.module import Base
from interface.motor_interface import MotorInterface
from core.configoption import ConfigOption


# Basic Python APT/Kinesis Command Protocol Example using KDC001 and MTS50-Z8
# Tested in Anaconda dsitrbution of Python 2.7 and virtual environment of Python 3.6
# Command Protol PDF can be found https://www.thorlabs.com/Software/Motion%20Control/APT_Communications_Protocol.pdf
# Pyserial is a not a native module installed within python and may need to be installed if not already

class MotorSerialKDC101(Base, MotorInterface):

    _address = ConfigOption('address', missing='error')

    def on_activate(self):
        self.pos = 0
        return

    def connection_on(self):
        return

    def connection_off(self):
        return

    def on_deactivate(self):
        return

    def able(self):
        return

    def disable(self):
        return

    def move_home(self):
        """Home Stage; MGMSG_MOT_MOVE_HOME: send the stage at home"""
        time.sleep(0.1)
        return

    def velocity(self):
        velmin = 0
        acc = 0.1
        velmax = 0.5
        self.dUnitvelmin = int(self.Device_Unit_Velocity * velmin)
        self.dUnitacc = int(self.Device_Unit_Acceleration * acc)
        self.dUnitvelmax = int(self.Device_Unit_Velocity * velmax)
        self.KDC001.write(pack('<HBBBBHIII', 0x0413, 0x0E, 0x00, self.destination | 0x80, self.source, self.Channel,
                               self.dUnitvelmin, self.dUnitacc, self.dUnitvelmax))

    def jog(self):
        return

    def jog_move(self):
        return

    def move(self, pos):
        """
        Move to absolute position; MGMSG_MOT_MOVE_ABSOLUTE (long version):
        set the position where you want to move the stage
        """
        time.sleep(0.1)
        self.pos = pos
        return

    def read_position(self):
        """Request Position; MGMSG_MOT_REQ_POSCOUNTER"""
        return self.pos

    def get_constraints(self):
        return 0

    def move_rel(self, param_dict):
        return 0

    def abort(self):
        return 0

    def get_pos(self, param_list=None):
        return 0

    def get_status(self, param_list=None):
        return 0

    def calibrate(self, param_list=None):
        return 0

    def get_velocity(self, param_list=None):
        return 0

    def set_velocity(self, param_dict):
        return 0

    def move_abs(self, param_dict):
        return 0

# del KDC001
