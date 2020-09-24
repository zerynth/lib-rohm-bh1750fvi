################################################################################
# Ambient light Example
#
# Created: 2020-08-03
# Author: S. Torneo
#
################################################################################

import streams
from rohm.bh1750fvi import bh1750fvi

streams.serial()

try:
    # Setup sensor 
    print("start...")
    sensor = bh1750fvi.BH1750FVI(I2C0)
    print("Ready!")
    print("--------------------------------------------------------")
except Exception as e:
    print("Error: ",e)

try:
    while True:
        ambient_light = sensor.get_value()
        print("Ambient light: ", ambient_light, "lx")
        print("--------------------------------------------------------")
        sleep(1000)
except Exception as e:
    print("Error2: ",e)
