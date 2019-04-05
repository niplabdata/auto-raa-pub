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


import os.path
import RPi.GPIO as GPIO
import time
from datetime import datetime
from decimal import *
##import Adafruit_ADS1x15
import math
import random
import smbus
import serial
import serial.tools.list_ports
import struct
import time
import shelve
import traceback
from potentiostat import Potentiostat
import logging

try:
    
    
                
    useLoadedVars = 0       # Set to 1 unless debugging code. A 1 will tell the RPi to use previous parameters.


    ### Vessel Parameters ###
    # Setup run parameters for each reaction module. Each module should have parameters at the same index in each list.
    experimentName = ['RAA_1', 'RAA_2']
    experimentEndDates = ["11/11/2018 10:00", "11/11/2018 10:00"]   # "DD/MM/YYYY hh:mm"
    ### Error with date format. may be MM/DD/YYYY hh:mm
    experimentRunParameters = [[15, 67], [15, 87]]                  # TARGET [H2O2], TEMP(C)
    experimentCurrToConcFunctions = [lambda x: 4.802*x + 0.739, lambda x: 42.37*x -1.327]
    echemRunParameters = [{"curr_range": '10uA',
                           "volt_range": '1V',
                           "low_volt": -0.3,
                           "high_volt": 0.7,
                           "low_volt_time": .5,
                           "high_volt_time": 2},
                          
                          {"curr_range": '10uA',
                           "volt_range": '1V',
                           "low_volt": -0.3,
                           "high_volt": 0.7,
                           "low_volt_time": .5,
                           "high_volt_time": 2}]
    pumpPins = [36,37]                                              # GPIO pins: [RAA 1 Pump, RAA 2 Pump]
    defaultPath = '/home/pi/Documents/RAA/RAA_Run_Data'                 # Parent directory for run data and saved parameters
    sampleRate = float(10**-1)                                          # Hz
    dataWriteRate = float(60**-1)                                       # Hz
    
##    pump_on_resolution = 15             # seconds



    bus = smbus.SMBus(1)    # Setup GPIO object
##    adc = Adafruit_ADS1x15.ADS1115()    # On board clock object
    numberOfRAAs = len(experimentName);     # Number of reaction modules based on length of list created above
    allTemps = [[] for k in range(numberOfRAAs)]        # Initiate run temp data 
    allH2O2Conc = [[] for k in range(numberOfRAAs)]     # Initiate run concentration data
    all_current = [float('nan') for k in range(numberOfRAAs)]
    echem_running_status = [False for k in range(numberOfRAAs)]
    echem_timing = [[] for k in range(numberOfRAAs)]
    new_current_available = [False for k in range(numberOfRAAs)]
    estimated_echem_end_time = [[] for k in range(numberOfRAAs)]
##    all_threads = [[] for k in range(numberOfRAAs)]
##    all_thread_init = [False for k in range(numberOfRAAs)]
    
    # Check RAA Dates. This checks that dates are in the correct format ("DD/MM/YYYY hh:mm")
    for k in range(numberOfRAAs):
        try:
           x = datetime.strptime(experimentEndDates[k], "%d/%m/%Y %H:%M")
        except:
            print 'Check date format for RAA #%i'%(k+1)
            quit()
    errorNum = 0
    dataLogFileName = list()
    # Create log file if it does not exist
    for k in range(numberOfRAAs):
        dataLogFileName.append(defaultPath + '/' + experimentName[k] + '.txt')
        
    GPIO.setmode(GPIO.BOARD)    # Setup GPIO map (BOARD = physical pin layout, BCM = GPIO pin numbering)
 
    for k in range(numberOfRAAs):
        print 'Experiment: %s'%experimentName[k]
        print 'File Dir: %s'%dataLogFileName[k]
        print 'End Date: %s'%experimentEndDates[k]
        t_end = datetime.strptime(experimentEndDates[k], "%d/%m/%Y %H:%M")
        t_end = (t_end - datetime.now()).total_seconds()
        print 'Seconds Until %s Ends: %s\n\n'%(experimentName[k],t_end)
    for k in range(len(pumpPins)):
        GPIO.setup(pumpPins[k], GPIO.OUT, initial=GPIO.LOW)

    ### Command List ###
    # The following two commands are for assigning a USB serial port to a reaction module temp or echem
    # controller. This is necessary when all 4 USB ports are being used by controllers. The run can be
    # initialized using a connected mouse and keyboard followed by disconnecting those peripherals and
    # connecting the 4 temp or echem controllers.
    def find_PID_serial_ports(num_RAAs):
        ser_ports = list(serial.tools.list_ports.comports())
        serialPID = [[] for x in range(num_RAAs)]
        for k in range(len(ser_ports)):
            for k1 in range(num_RAAs):
                ser = serial.Serial(ser_ports[k][0], 9600, timeout = 0)
                ser.flushInput()
                ser.flushOutput()
                cT = ser.readlines()
                string = '*00'+str(k1+1)+'G110 \r\r'
                ser.flushInput()
                ser.flushOutput()
                ser.write(string)
                ser.flushInput()
                ser.flushOutput()
                time.sleep(.1)
                cT = ser.readlines()
                ser.flushInput()
                ser.flushOutput()
                ser.close()
                if cT:
                    serialPID[k1] = ser_ports[k][0]
        return serialPID

    # Find and link Arduino to a module number
    def find_arduino_serial_ports(num_RAAs):
        _Ard_Address = [[] for x in range(num_RAAs)]
        ports = list(serial.tools.list_ports.comports())
        print 'Looking for ARD port...'
        for p in ports:
            try:
##                print p
                dev = Potentiostat(p[0])
                cT = dev.get_device_id()
                if float(cT) == 1:
                    print 'Connecting RAA 1 to Arduino (ID: %s) via port %s.'%(str(cT), p[0])
                    _Ard_Address[0] = dev
                if float(cT) == 2:
                    print 'Connecting RAA 2 to Arduino (ID: %s) via port %s.'%(str(cT), p[0])
                    _Ard_Address[1] = dev
            except:
                pass
##                print 'Could not connect to arduino (Ln: 140)'
        if not _Ard_Address[0]:
            print 'Could not connect RAA 1 to potentiostat'
        if not _Ard_Address[1]:
            print 'Could not connect RAA 2 to potentiostat'
        return _Ard_Address

    # Talk to the temperature controller and get the current temp value.
    def get_current_temperature(_serialPID):
        ser = serial.Serial(_serialPID, 9600, timeout = 0)
        ser.write("*G110 \r")
        ser.flushInput()
        ser.flushOutput()
        time.sleep(.1)
        cT = ser.readlines()
        ser.close()
        return float(cT[0])


    # Log the current experimental values
    def Write_To_RAA_File(log_file_name, new_line):
        current_time = datetime.now()
        current_time = current_time.timetuple()
        current_time = str(current_time[0:6])
        current_time = current_time[1:(len(current_time)-1)]
        current_time = current_time+', '+str(int(math.floor(math.modf(time.time())[0]*1000)))
        
        for k in range(len(new_line)):
            new_line[k] = str(new_line[k])
        new_line = [current_time] + new_line
        new_line = '\t'.join(new_line)
        new_line = new_line + '\n'
        with open(log_file_name, 'a') as RAAFile:
            #print new_line
            RAAFile.write(new_line)
            



    # Manage a list of values for temperature and concentration. This is so a running average can be used if
    # necessary.
    def Add_Value_To_Data_List(old_vals, new_val, lenLimit):
        if len(old_vals) >= lenLimit:
            old_vals = old_vals[1:(len(old_vals))]
        old_vals = old_vals + [new_val]
        return old_vals


##    class peristaltic_thread (threading.Thread):
##        def __init__(self, on_fraction, gpio_pin):
##            threading.Thread.__init__(self)
##            self.on_fraction = on_fraction
##            self.gpio_pin = gpio_pin
##        def run(self):
##            try:
##                operate_pump(self.on_fraction, self.gpio_pin)
##            except:
##                pass
##
##    def operate_pump(on_fraction, pin_number):
##        GPIO.output(pin_number, GPIO.HIGH)
##        time.sleep(pump_on_resolution*on_fraction)
##        GPIO.output(pin_number, GPIO.LOW)
        
##    # Create thread to run each potentiostat independantly without interrupting main script
##    class potentiostat_thread (threading.Thread):
##        def __init__(self, threadID, device_address):
##            threading.Thread.__init__(self)
##            self.threadID = threadID
##            self.portNum = device_address
##        def run(self):
##            print "Starting " + str(self.threadID)
##            try:
##                curr = run_rodeo(self.threadID, self.portNum)
##             ##  print "Finishing " + str(self.threadID)
##            except:
##                curr = float('nan')
##           ## print 'RAA %i Current: %f'%(self.threadID + 1, curr)
##            global all_current
##            all_current[self.threadID] = curr
##          
##
##    # Potentiostat method used by threads
##    def run_rodeo(threadID, device_ID):
##        curr_range = '10uA'
##        volt_range = '1V'
##        low_volt = -0.3             # Volts 
##        high_volt = 0.7             # Volts
##        low_volt_time = .5          # Seconds
##        high_volt_time = 2          # Seconds
##        sample_period = 0.1
##
##    
####        print 'Attempting to talk to Potentiostat %i'%(thread_ID + 1)
##        device_ID.set_curr_range(curr_range)
##        device_ID.set_volt_range(volt_range)
####        print 'Successfully talked to Potentiostat %i'%(thread_ID + 1)
##
##        device_ID.set_volt(low_volt)
##        time.sleep(low_volt_time)
##        device_ID.set_volt(high_volt)
##        time.sleep(high_volt_time)
##        current = device_ID.get_curr()
##        device_ID.set_volt(0)
##        return current

    def run_rodeo_synchronized(device_ID, echem_timer, echem_parameters):
##        print echem_parameters
        curr_range = echem_parameters['curr_range']
        volt_range = echem_parameters['volt_range']
        low_volt = echem_parameters['low_volt']
        high_volt = echem_parameters['high_volt']
        low_volt_time = echem_parameters['low_volt_time']
        high_volt_time = echem_parameters['high_volt_time']
##        curr_range = '10uA'
##        volt_range = '1V'
##        low_volt = -0.3             # Volts 
##        high_volt = 0.7             # Volts
##        low_volt_time = .5          # Seconds
##        high_volt_time = 2          # Seconds

        current = float('nan')
        try:
##            print 'Rodeo code for %s'%(str(device_ID.get_device_id()))
            if not device_ID.get_curr_range() == curr_range:
                device_ID.set_curr_range(curr_range)
            if not device_ID.get_volt_range() == volt_range:
                device_ID.set_volt_range(volt_range)
                
            if abs(echem_timer - time.time()) < low_volt_time:
##                print 'Timer: %s\nCurrent time: %s\nLow volt time: %s'%(str(echem_timer), str(time.time()), str(echem_timer-time.time()))
                if not round(device_ID.get_volt()*10)/10 == round(low_volt*10)/10:
                    print 'Setting potentiostat %s to %sV'%(str(device_ID.get_device_id()), str(low_volt))
                    device_ID.set_volt(low_volt)
            elif (abs(echem_timer - time.time()) > low_volt_time) and (abs(echem_timer - time.time()) < (high_volt_time + low_volt_time)):
                if not round(10*device_ID.get_volt())/10 == round(10*high_volt)/10:
                    print 'Setting potentiostat %s to %sV'%(str(device_ID.get_device_id()), str(high_volt))
                    device_ID.set_volt(high_volt)
            elif (abs(echem_timer - time.time()) > (high_volt_time + low_volt_time)):
                if not round(device_ID.get_volt()*10)/10 == 0:
                    current = device_ID.get_curr()
                    print 'Setting potentiostat %s to %sV. Current is %s'%(str(device_ID.get_device_id()), str(0), str(current))
                    device_ID.set_volt(0)
        except Exception as ex:
            pass
##            logging.exception("message")
        return current
        






    # Initialize communication with peripherals
    time.sleep(1)
    RAA_Temp_Comm = find_PID_serial_ports(numberOfRAAs)
    time.sleep(2)
    Ard_Address = find_arduino_serial_ports(numberOfRAAs)
    
    
    currentRAA = 0;
    lastSampleTime = time.time()
    lastWriteTime = lastSampleTime
    allRAANotComplete = True
    temperatureErrorCount = 0;
    ardErrorCount = 0;

    while allRAANotComplete:
        currentRAA = currentRAA + 1
        if currentRAA > numberOfRAAs:
            currentRAA = 1
        # Check if run is finished
        if datetime.now() > datetime.strptime(experimentEndDates[currentRAA-1], "%d/%m/%Y %H:%M"):
            for key in dir():
                if globals()[key].__class__ is list:
                    if len(globals()[key]) == numberOfRAAs:
                        try:
                            del globals()[key][currentRAA-1]
                        except:
                            pass
            numberOfRAAs = numberOfRAAs - 1
            if numberOfRAAs == 0:
                allRAANotComplete = False
                print "Run over"
            continue
        
        if useLoadedVars == 1 and os.path.isfile(defaultPath + '/wsvars.out'):
            print 'Loading previous session...'
            recovFile = shelve.open(defaultPath + '/wsvars.out', 'r')
            for key in recovFile:
                globals()[key] = recovFile[key]
            recovFile.close()
            # Reset start timer using the elapsed time from previous session
            startTimer = time.time() - (currentTimer - startTimer)
            currentTimer = time.time()
            useLoadedVars = 0

            
        pumpPinVals = [0 for k in range(numberOfRAAs)]
        # Determine State of Pins
        for k in range(numberOfRAAs):
            try:
##                _H2O2Temp = []
##                k1 = len(allH2O2Conc[k]) - 1
##                while _H2O2Temp == []:
##                    if not math.isnan(allH2O2Conc[k][k1]):
##                        _H2O2Temp = allH2O2Conc[k][k1]
##                    elif k1 == 0:
##                        _H2O2Temp = float('nan')
##                    k1 -= 1
                
                _H2O2Temp = allH2O2Conc[k][-1]
                if _H2O2Temp < experimentRunParameters[k][0]:
                    pumpPinVals[k] = 1
            except:
                pass
        GPIO.output(pumpPins, pumpPinVals)

        # Set status of echem methods
        for k in range(numberOfRAAs):
            if echem_running_status[k]:
##                print 'Line 339: %s'%(str(Ard_Address[k].get_device_id()))
                curr = run_rodeo_synchronized(Ard_Address[k], echem_timing[k], echemRunParameters[k])
                if not math.isnan(curr):
                    echem_running_status[k] = False
                    all_current[k] = curr
                    new_current_available[k] = True
        # Get data at frequency as defined in parameters
        if (time.time()-lastSampleTime) > (1/sampleRate):
            for k in range(numberOfRAAs):


                #######  Get echem values  #######
                try:
                    # Check if echem cycle should be done by now (at least double the cycle time)
                    if not not estimated_echem_end_time[k]:
                        if time.time() > estimated_echem_end_time[k]:
                            print 'Too much time has passed, skipping echem for RAA %s'%(str(k + 1))
                            estimated_echem_end_time[k] = []
                            echem_running_status[k] = False
                            new_current_available[k] = True
                    # Check if potentiostat is connected
                    if not Ard_Address[k] == []:
                        # If potentiostat is connected, check status of echem cycle
                        if not echem_running_status[k]:
                            echem_timing[k] = time.time()
                            echem_running_status[k] = True
                            x = echemRunParameters[k]['low_volt_time'] + echemRunParameters[k]['high_volt_time']
                            estimated_echem_end_time[k] = echem_timing[k] + (x*2)
                
                    # Get latest current value
                    H2O2Val = all_current[k]
                    print H2O2Val
                    # Convert latest current to [H2O2]
                    H2O2Val = experimentCurrToConcFunctions[k](H2O2Val)
                    # Check that there is one non-nan value in H2O2 history (to stabilize pump switching)
                    concTemp = allH2O2Conc[k] + [H2O2Val]
                    H2O2ValLast = []
                    k1 = len(concTemp) - 1
                    while H2O2ValLast == []:
                        if not math.isnan(concTemp[k1]):
                            H2O2ValLast = concTemp[k1]
                        elif k1 == 0:
                            H2O2ValLast = float('nan')
                        k1 -= 1
                    # If there is no non-nan value in H2O2 history, concider it an error
                    if math.isnan(H2O2ValLast):
##                        # Check if echem is running before throwing an error (it may not be finished yet)
##                        if echem_running_status[k]:
##                            # If echem is running, check if it has been more than 5 seconds past scheduled finish time
##                            if ((echem_timing[k] - time.time()) >
##                                (5 + echemRunParameters[k]['high_volt_time'] + echemRunParameters[k]['low_volt_time'])):
                        ardErrorCount += 1
                        print 'Error: No history of non-nan value RAA %s\nArduino error count: %s'%(str(k + 1), str(ardErrorCount))
                    if ardErrorCount > 5:
                        print 'Attempting to reconnect to Arduinos...\n'
                        Ard_Address = find_arduino_serial_ports(numberOfRAAs)
##                        print 'Line 382: %s'%(str(Ard_Address[0].get_device_id()))
                        ardErrorCount = 0
                except:
                    H2O2Val = float('nan')
                    ardErrorCount = ardErrorCount + 1
                    print 'Error: exception caught for RAA %s\nArduino error count: %s'%(str(k + 1), str(ardErrorCount))
                    if ardErrorCount > 5:
                        print 'Attempting to reconnect to Arduinos...\n'
                        Ard_Address = find_arduino_serial_ports(numberOfRAAs)
##                        print 'Line 390: %s'%(str(Ard_Address[0].get_device_id()))
                        ardErrorCount = 0
                    print 'Failed to read concentration for %s.'%(experimentName[k])
                if new_current_available[k]:
                    allH2O2Conc[k] = Add_Value_To_Data_List(allH2O2Conc[k], H2O2Val, 5)
                    print allH2O2Conc[k]
                    new_current_available[k] = False


                #######  Get temperature values  #######
                try:
                    currentTemp = get_current_temperature(RAA_Temp_Comm[k])
                except:
                    currentTemp = float('nan')
                    temperatureErrorCount = temperatureErrorCount + 1
                    if temperatureErrorCount > 5:
                        print 'Attempting to reconnect to PID controllers...\n'
                        RAA_Temp_Comm = find_PID_serial_ports(numberOfRAAs)
                        temperatureErrorCount = 0
                    print 'Failed to read temp for %s.'%(experimentName[k])
                allTemps[k] = Add_Value_To_Data_List(allTemps[k], currentTemp, 5)
            lastSampleTime = time.time()


        # Write data to file at frequency as defined in parameters
        if (time.time()-lastWriteTime) > (1/dataWriteRate):
            for k in range(numberOfRAAs):
                _H2O2Conc = [x for x in allH2O2Conc[k] if not math.isnan(x)]
                _H2O2Conc = float(sum(_H2O2Conc)/max(len(_H2O2Conc),1))
                _Temperature = [x for x in allTemps[k] if not math.isnan(x)]
                _Temperature = float(sum(_Temperature)/max(len(_Temperature),1))
                print 'RAA%i Conc: %.2f    Temp: %.2f\n'%(k+1, _H2O2Conc, _Temperature)
                
                # Write variables to file in case of failure
                if os.path.isfile(defaultPath + '/wsvars.out'):
                    os.remove(defaultPath + '/wsvars.out')
                recovFile = shelve.open(defaultPath + '/wsvars.out', 'n')
                for key in dir():
                    try:
                        recovFile[key] = globals()[key]
                    except:
##                        print('Error shelving: {0}'.format(key))
                        pass
                recovFile.close()
                useLoadedVars = 0

                # Write RAA vessel data to file
                
                Write_To_RAA_File(dataLogFileName[k], [_Temperature, \
                                                       _H2O2Conc])
            lastWriteTime = time.time()
            





except:
    traceback.print_exc()
    pass
finally:
    GPIO.cleanup()
    ports = list(serial.tools.list_ports.comports())
    for p in ports:
        try:
            dev = Potentiostat(p[0])
            dev.stop_test()
        except:
            pass

