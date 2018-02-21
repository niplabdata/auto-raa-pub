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
curr_range = '10uA'     # Name of current range for test [-10uA, +10uA]
volt_range = '1V'
low_voltage = -0.3
low_time = .5
high_voltage = 0.7
high_time = 2
sample_period = .1

try: 
    dev = []
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        try:
            dev_temp = Potentiostat(p[0])
            cT = dev_temp.get_device_id()
            if cT == potentiostat_ID:
                dev = dev_temp
        except:
            pass

    if not dev == []:
        print 'Running chronoamperometry on potentiostat with device ID: %s'%(str(dev.get_device_id()))
        dev.set_volt_range(volt_range)
        dev.set_curr_range(curr_range)
        ##dev.stop_test()

        list_length = 1
        curr_list = []
        while True:
            stTime = time.time()
            run_pot = True
            hold_period = False
##            sample_period = .1
            sample_time = time.time()
            num_samples = 0
            total_curr = 0
            print "Holding Low"
            dev.set_volt(low_voltage)
            while run_pot:
                if time.time() - stTime > low_time:
                    if not hold_period:
                        print "Holding High"
                        dev.set_volt(high_voltage)
                        hold_period = True
                    if time.time() - stTime > low_time + (high_time/2):
                        if time.time() - sample_time > sample_period:
##                            print dev.get_curr()
                            total_curr += dev.get_curr()
                            num_samples += 1
                            sample_time = time.time()
                if time.time() - stTime > low_time + high_time:
                    run_pot = False
            if curr_list == []:
                curr_list = [total_curr/num_samples]
            elif len(curr_list) < list_length:
                curr_list = curr_list + [total_curr/num_samples]
            else:
                curr_list = curr_list[1:len(curr_list)] + [total_curr/num_samples]
            curr = sum(curr_list)/len(curr_list)
            print "Current: %f"%(curr)
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
    










