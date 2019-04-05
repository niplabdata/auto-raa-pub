#Disclaimer: 
#The current document is distributed as supplementary material for the following publication (not peer-reviewed):
#"Automated Reactive Accelerated Aging for Rapid In Vitro Evaluation of Neural Implants Performance" 
#by Matthew G. Street, Cristin G. Welle, and Pavel A. Takmakov
#doi: https://doi.org/10.1101/204099 
#https://www.biorxiv.org/content/early/2017/10/17/204099
#The views, opinions, and/or findings contained in this document are those of the authors and should not be interpreted 
#as representing the official views or policies of Department of Health and Human Services or the U.S. Government. 
#The mention of commercial products, their sources, or their use in connection with material reported herein
#is not to be construed as either actual or implied endorsement of such products by the Department of Health and Human Services.
#The authors assume no responsibility whatsoever for use of the automated Reactive Accelerated Aging (aRAA) 
#by other parties and make no guarantees, expressed or implied, about the quality, reliability, 
#or any other characteristic of the system. 
#Further, use of the aRAA in no way implies endorsement by the FDA or confers any advantage in regulatory decisions. 
#Any use of the aRAA is to be cited as stipulated in the license agreement. 
#In addition, any derivative work shall bear a notice that it is sourced from the aRAA, 
#and any modified versions shall additionally bear the notice that they have been modified.




from potentiostat import Potentiostat
import time
import serial
import serial.tools.list_ports
import traceback

potentiostat_ID = 2

try: 
    dev = 1
    devices_found = 0
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        if not (devices_found > 0):
            try:
                dev = Potentiostat(p[0])
                serial_port = p[0]
                devices_found += 1
            except:
                pass

    if not dev == []:
        dev.set_device_id(potentiostat_ID)
        print 'Setting potentiostat on port %s with ID: %s'%(str(serial_port), str(dev.get_device_id()))
        if devices_found > 1:
            print '***********\n**Warning**\n***********'
            print 'Multiple potentiostats detected'
    else:
        print 'Could not connect potentiostat with device ID: %s'%(str(potentiostat_ID))

except:
    traceback.print_exc()
    pass
finally:
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        try:
            dev = Potentiostat(p[0])
            dev.stop_test()
        except:
            pass
    










