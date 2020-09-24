# Zerynth - libs - rohm-bh1750fvi/bh1750fvi.py
#
# Zerynth library for BH1750FVI ambient light sensor
#
# @Author: Stefano Torneo
#
# @Date: 2020-08-03
# @Last Modified by: Stefano Torneo
# @Last Modified time: 2020-09-04

"""
.. module:: BH1750FVI

**************
BH1750FVI Module
**************

.. _datasheet: https://eu.mouser.com/datasheet/2/348/Rohm_11162017_ROHMS34826-1-1279292.pdf

This module contains the Zerynth driver for BH1750FVI digital ambient light sensor. 
The BH1750FVI features a I2C digital interface. 
It is possible to detect wide scale at High resolution. (1 - 65535 lx). 

"""

import i2c

# Define some constants from the datasheet

POWER_DOWN = 0x00 # No active state.
POWER_ON   = 0x01 # Waiting for measurement command. 
RESET      = 0x07 # Reset data register value.
# Start measurement at 4lx resolution. Time typically 16ms.
CONTINUOUS_LOW_RES_MODE = 0x13
# Start measurement at 1lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_1 = 0x10
# Start measurement at 0.5lx resolution. Time typically 120ms
CONTINUOUS_HIGH_RES_MODE_2 = 0x11
# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_1 = 0x20
# Start measurement at 0.5lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_HIGH_RES_MODE_2 = 0x21
# Start measurement at 1lx resolution. Time typically 120ms
# Device is automatically set to Power Down after measurement.
ONE_TIME_LOW_RES_MODE = 0x23

MEASUREMENT_TIME_H = 0x40  # changing measurement time register MSB bits
MEASUREMENT_TIME_L = 0x60  # changing measurement time register LSB bits

# MTREG Values
MTREG_DEFAULT = 69
MTREG_MIN = 31          
MTREG_MAX = 254 

# Sensitivity Values
SENSITIVITY_MIN = 0.45
SENSITIVITY_MAX = 3.68
SENSITIVITY_DEFAULT = 1.00

# Accuracy Values
ACCURACY_MIN = 0.96
ACCURACY_MAX = 1.44
ACCURACY_DEFAULT = 1.2 
    
class BH1750FVI(i2c.I2C):
    """
    
===============
 BH1750FVI class
===============

.. class:: BH1750FVI(drvname, addr=0x23, clk=400000)

    Creates an intance of the BH1750FVI class.

    :param drvname: I2C Bus used '( I2C0, ... )'
    :param addr: Slave address, default 0x23
    :param clk: Clock speed, default 400kHz
    
    Ambient light value can be easily obtained from the sensor: ::

        from rohm.bh1750fvi import bh1750fvi

        ...

        sensor = bh1750fvi.BH1750FVI(I2C0)

        ambient_light = sensor.get_value()

    """
    
    """ Implement BH1750 communication. """
    
    # list of measurement mode
    list_meas_mode = [
        ONE_TIME_HIGH_RES_MODE_1,
        ONE_TIME_HIGH_RES_MODE_2,
        ONE_TIME_LOW_RES_MODE,
        CONTINUOUS_HIGH_RES_MODE_1,
        CONTINUOUS_HIGH_RES_MODE_2,
        CONTINUOUS_LOW_RES_MODE
    ]

    def __init__(self, drvname, addr=0x23, clk=400000):
        
        if (addr != 0x23 and addr != 0x5c):
            raise ValueError

        i2c.I2C.__init__(self,drvname,addr,clk)
        try:
            self.start()
        except PeripheralError as e:
            print(e)
            
        self.set_mode(POWER_DOWN)
        self.set_sensitivity()
        self.set_accuracy()
        self.set_resolution()
    
    ##
    ## @brief      Set the current mode passed as argument.
    ##
    ## @param      mode     is the mode to set.
    ## @return     nothing
    ##
    def set_mode(self, mode):
        self.mode = mode
        self.write_bytes(self.mode)

    ##
    ## @brief      Set the current mode to "reset" in order to reset data register value.
    ##             Reset command is not acceptable in Power Down mode.
    ##
    ## @return     nothing
    ##
    def reset(self):
        self.set_mode(POWER_ON) # It has to be powered on before resetting
        self.set_mode(RESET)

    def set_sensitivity(self, sensitivity=1):
        """
    .. method:: set_sensitivity(sensitivity = 1) 
        
        :param sensitivity: is the sensitivity to set (default value = 1).

        Sensitivity scale is 0.45-3.68, typical value is 1.

        Set the sensor sensitivity value.

        """

        # calculating MTreg value for new sensitivity
        valueMTreg = sensitivity * MTREG_DEFAULT

        # safety check, make sure valueMTreg never exceeds the limits
        if (valueMTreg < MTREG_MIN):
            self.mtreg   = MTREG_MIN
            self.sensitivity = SENSITIVITY_MIN
        elif (valueMTreg > MTREG_MAX):
            self.mtreg   = MTREG_MAX
            self.sensitivity = SENSITIVITY_MAX
        else:
            self.mtreg = valueMTreg
            self.sensitivity = sensitivity

        meas_TimeHighBit = self.mtreg
        meas_TimeLowBit  = self.mtreg

        # high bit manipulation
        meas_TimeHighBit >>= 5
        meas_TimeHighBit |= MEASUREMENT_TIME_H # 0,1,0,0,0,MT[7-bit,6-bit,5-bit]
       
        # low bit manipulation
        meas_TimeLowBit <<= 3
        meas_TimeLowBit >>= 3
        meas_TimeLowBit |= MEASUREMENT_TIME_L # 0,1,1,MT[4-bit,3-bit,2-bit,1-bit,0-bit]
        
        # update sensor Measurment Timer register
        self.write_bytes(meas_TimeHighBit)
        self.write_bytes(meas_TimeLowBit)
        
    def get_sensitivity(self):
        """
    .. method:: get_sensitivity() 

        Return the sensitivity set.

        """
        return self.sensitivity
    ##
    ## @brief      Get current measurement result in lx. 
    ##
    ## @return     current measurement result in lx.
    ##
    def get_result(self):
        data = self.read(n=2)
        high_bytes = data[0]
        low_bytes = data[1]
        res = low_bytes + (256 * high_bytes)
        return res

    ##
    ## @brief      Wait the delay to get result.
    ##
    ## @param      mode         is the measurement mode.
    ## @return     nothing
    ##
    def wait_for_result(self, mode):
        # if measurement mode is low
        if (mode & 0x03) == 0x03:
            basetime = 16
        else:
            basetime = 120
        
        wait_time = int(basetime * self.sensitivity)
        sleep(wait_time)

    ##
    ## @brief      Perform complete measurement using command specified by parameter mode.
    ##           
    ## 
    ## @param      mode     is the measurement mode.
    ## @return     measurement value in lx.
    ##
    def do_measurement(self, mode):
        self.reset()
        self.write_bytes(mode)
        self.wait_for_result(mode)
        return self.get_result()

    def set_accuracy(self, accuracy=1.2):
        """
    .. method:: set_accuracy(accuracy = 1.2) 
        
        :param accuracy: is the accuracy to set (default value = 1.2).

        Accuracy scale is 0.96-1.44, typical value is 1.2.

        Set the sensor accuracy value.

        """
        # safety check, make sure value never exceeds calibration scale
        if (accuracy < ACCURACY_MIN):
            self.accuracy = 0.96
        elif (accuracy > ACCURACY_MAX):
            self.accuracy = 1.44
        else:
            self.accuracy = accuracy

    def get_accuracy(self):
        """
    .. method:: get_accuracy() 

        Return the accuracy set.

        """
        return self.accuracy

    def set_resolution(self, res=1):
        """
    .. method:: set_resolution(res = 1) 
    
        **Parameters**:
        
        **res**: is the resolution to set (default value = 1).

        ======== =====================
         res      Resolution
        ======== =====================
         1         One measurement, 1.0 lx resolution
         2         One measurement, 0.5 lx resolution
         3         One measurement, 4 lx resolution
         4         Continous measurement, 1.0 lx resolution
         5         Continous measurement, 0.5 lx resolution
         6         Continous measurement, 4 lx resolution
        ======== =====================
        
        Set the sensor resolution value.

        """
        if (res not in [1, 2, 3, 4, 5, 6]):
            raise ValueError

        self.resolution = self.list_meas_mode[res-1]
    
    def get_resolution(self):
        """
    .. method:: get_resolution() 

        Return the resolution set.
        """
        return self.list_meas_mode.index(self.resolution) + 1

    def get_value(self):
        """
    .. method:: get_value()    

        Return the ambient light value in lx.
        
        """
        raw_value = self.do_measurement(self.resolution)

        light = raw_value / (self.accuracy * self.sensitivity)

        # if resolution is 0.5 lx
        if (self.get_resolution() in [2, 5]):
            light *= 0.5
        
        return light