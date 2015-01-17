""" This module contains functions for running experiments with Keithley
    6220/2182A IV-curves, nidaq, and magnet. 

    IV_DAQgate -- Sources current(voltage) and measures voltage (current) 
                  using the 6220/2182A to run and IV curve and the NIDAQ 
                  to supply a single gate voltage. Returns current vs bias
                  vs gate. 
                  
    IV_MagField -- Sources current(voltage) and measures voltage (current) 
                   using the 6220/2182A to run and IV curve and the IPS120
                   to supply a magnetic field. Returns current vs bias vs 
                   field. 
                   
                   NOTE: This is not yet tested. """

from __future__ import division
import time, os
import msvcrt
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import nidaqmx
import exptools as tools
import instruments
import keithleypair
from threading import Thread
    
class IV_MagField():

    """ Use the Keithley 6220 and 2182A to sweep IV curves for different
        magnetic fields. The function will save a plot each IV curve as it runs. 
        
        fieldLim/biasLim should be an array with 3 elements [start, stop, step] 
        given in Tesla/Volts. 
        
        Be sure to optimize the nanovoltmeter range. Setting it to 'auto' 
        is quite slow.
        
        If you are sourcing current and measuring voltage, set the cvAmp and
        current to voltage resistor to 1.0 
        
        To run:  measurement = keithleypair_IV_Var.IV_MagField()
                 measurement.run(biasLim, fieldLim, ...)
                 
                 End early with 'q'. Do NOT close the plot before ending
                 the sweep. """
    
    def __init__(self, filename = 'iv-DAQgate_{0:.0f}'.format(time.time())):
    
        """ opens a file for the experiment. this means you have to start a new instance
            of the class each time you want a new file. strange. maybe ok? """

        self.filename = filename
        self.file = open(filename+'.dat','a')
    
    def run_simple(biasLim, fieldLim, gate = 0.0, ivAvg = 1,
                    cvResistor = 10.0, cvAmp = -1e-6, gateAmp = 9.1788, 
                    srcDelay = 0.01, fieldDelay = 2.0, 
                    nplc = 1, nvmRange = 0.1):
                    
        """ Runs the actual experiment. Can be called directly if plotting is
            not needed. """
            
        tools.write_log('iv_magField', locals(), filename+'.log')
        
        biasBuffer = tools.get_buffer_size(biasLim[0], biasLim[1], biasLim[2]) 
        bias = np.linspace(biasLim[0], biasLim[1], biasBuffer)
        np.savetxt(file, [np.insert(bias, 0, 0.0)], fmt = '%+.6e', delimiter = '\t')
        fieldBuffer = tools.get_buffer_size(fieldLim[0], fieldLim[1], fieldLim[2]) 
        fields = np.linspace(fieldLim[0], fieldLim[1], fieldBuffer) 
        
        source = keithleypair.IVmax1024("GPIB::22", timeout = 60.0) #keithley object
        mag = instruments.oxford_magnet("GPIB::20", rate = 0.2, timeout = 60.0)
        daqGate = nidaqmx.AnalogOutputTask() #DAQ output object
        daqGate.create_voltage_channel('Dev1/ao0', min_val = -10.0, max_val = 10.0)
        daqGate.write([gate/gateAmp])
        time.sleep(1.0)
            
        #setup sweep and nanovoltmeter parameters
        source.general_setup(beep = True)
        currLim = [x/cvResistor for x in biasLim] 
        source.source_sweep_setup(currLim[0], currLim[1], currLim[2], srcDelay)
        source.source_arm_setup()
        source.source_trig_setup()
        source.voltmeter_channel_setup(nplc, nvmRange, digital_filter = False)
        source.voltmeter_trig_setup() 
        source.voltmeter_buffer_setup(biasBuffer)
        realBuffer = int(source.ask(':sour:swe:poin?'))
        if int(biasBuffer) != realBuffer:
            raise RuntimeError('buffer sizes do not match: {0}, {1}'.format(int(biasBuffer), realBuffer))
        
        #check that everything is setup
        print 'source state    = {}'.format(source.source_chk_op_evnt_reg())
        print 'voltmeter state = {}'.format(source.voltmeter_chk_meas_evnt_reg())
        
        #arm sweep
        source.write_serial(':init:imm')
        time.sleep(0.25)
        source.write(":sour:swe:arm")
        time.sleep(3.0)
        
        mag.go_to_field(fieldLim[0], fieldDelay)
        
        for field in fields:
            print 'running IV for field = {}T'.format(field)
            mag.go_to_field(field, fieldDelay)
            data = np.array(source.execute_sweep(ivAvg = ivAvg, timeout = 120.0), dtype = np.floating)
            data = data*cvAmp #calculate current from voltage measurement
            for i in range(ivAvg): #save all data before averaging
                np.savetxt(file, [np.insert(data[i], 0, field)], fmt = '%+.6e', delimiter = '\t')
                self.file.flush(); os.fsync(self.file)
                print data[i][0], data[i][1], '...', data[i][-2], data[i][-1]
            data = data.mean(axis = 0) #average over multiple IV curves for plot
            
            if msvcrt.kbhit():
                if ord(msvcrt.getch()) == 113:
                    print "Program ended by user.\n"
                    break 
        print 'Cleaning up...'
        source.write(":outp 0") #turn off current source
        source.close()
        mag.end_at_zero() #set field back to zero
        mag.close()
        daqGate.write([0.0]) #turn off gate
        del mag, source, daqGate
        self.file.close()
        
    def run(self, *args, **kwargs):
    
        """ This will run the animation as the main thread and start a 
            second thread for the measurement.
            
            Takes all of the arguments and keyword arguments and passes them
            to self.run_simple """
        
        runArgs = args
        runKwargs = kwargs
        fileName = self.filename+'.dat'
        
        def update_iv_field(num, fileName, title_text, line, ax):
            data = np.loadtxt(fileName, dtype = np.floating)
            line.set_ydata(data[-1,1:])
            ax.set_ylim(np.amin(data[-1,1:]), np.amax(data[-1,1:])) 
            title_text.set_text('field = {}T'.format(data[-1,0]))
            return line, title_text, ax
    
        t = Thread(target = self.run_simple, args = runArgs, kwargs = runKwargs)
        t.start()
        time.sleep(5.0)
        
        r = 0
        while r <2:
            data = np.loadtxt(fileName)
            r = np.shape(data)[0]  #wait for at least two rows to plot
            
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlim(data[0,1], data[0,-1])
        ax.set_ylim(data[1,1]*1.25, data[1,-1]*1.25)
        title_text = plt.title('gate = {}'.format(data[1, 0]))
        line, = ax.plot(data[0,1:], data[1,1:],'r-')
        plt.xlabel('bias')
        plt.ylabel('measured')

        line_ani = animation.FuncAnimation(fig, update_iv_gate, fargs=(fileName, title_text, line, ax),
            interval=1000, blit=False)

        plt.show()

class IV_DAQgate():

    """ Use the Keithley 6220 and 2182A to sweep IV curves for different
        gate voltages. The function will save a plot each IV curve as it runs. 
        
        gateLim and biasLim should be arrays with 3 elements 
        [start, stop, step] given in volts. 
        
        Be sure to optimize the nanovoltmeter range. Setting it to 'auto' 
        is quite slow.
        
        If you are sourcing current and measuring voltage, set the cvAmp and
        current to voltage resistor to 1.0 
        
        To add a magnetic field, set it up manually. The field variable only 
        exists for logging purposes 
        
        To run:  measurement = keithleypair_IV_Var.IV_DAQgate()
                 measurement.run(biasLim, gateLim, ...)
                 
                 End early with 'q'. Do NOT close the plot before ending
                 the sweep. """
        
    def __init__(self, filename = 'iv-DAQgate_{0:.0f}'.format(time.time())):
    
        """ opens a file for the experiment. this means you have to start a new instance
            of the class each time you want a new file. strange. maybe ok? """

        self.filename = filename
        self.file = open(filename+'.dat','a')
    
    def run_simple(self, biasLim, gateLim, field = 0.0, ivAvg = 1,
               cvResistor = 10.0, cvAmp = -1e-6, gateAmp = 9.1788, 
               srcDelay = 0.01, gateDelay = 1.0, nplc = 1, nvmRange = 0.1):
      
        """ Runs the actual experiment. Can be called directly if plotting is
            not needed. """
            
        tools.write_log('iv_DAQgate', locals(), self.filename+'.log') #save hacked log-file
    
        biasBuffer = tools.get_buffer_size(biasLim[0], biasLim[1], biasLim[2]) 
        bias = np.linspace(biasLim[0], biasLim[1], biasBuffer)
        data = np.zeros(biasBuffer)
        gateBuffer = tools.get_buffer_size(gateLim[0], gateLim[1], gateLim[2]) 
        gates = np.linspace(gateLim[0], gateLim[1], gateBuffer) 
        
        source = keithleypair.IVmax1024("GPIB::22", timeout = 30.0) #keithley object
        daqGate = nidaqmx.AnalogOutputTask() #DAQ output object
        daqGate.create_voltage_channel('Dev1/ao0', min_val = -10.0, max_val = 10.0)
        
        #setup sweep and nanovoltmeter parameters
        source.general_setup(beep = True)
        currLim = [x/cvResistor for x in biasLim] 
        source.source_sweep_setup(currLim[0], currLim[1], currLim[2], srcDelay)
        source.source_arm_setup()
        source.source_trig_setup()
        source.voltmeter_channel_setup(nplc, nvmRange, digital_filter = False)
        source.voltmeter_trig_setup() 
        source.voltmeter_buffer_setup(biasBuffer)
        realBuffer = int(source.ask(':sour:swe:poin?'))
        if int(biasBuffer) != realBuffer:
            raise RuntimeError('buffer sizes do not match: {0}, {1}'.format(int(biasBuffer), realBuffer))
        
        #check that everything is setup
        print 'source state    = {}'.format(source.source_chk_op_evnt_reg())
        print 'voltmeter state = {}'.format(source.voltmeter_chk_meas_evnt_reg())
        
        #arm sweep
        source.write_serial(':init:imm')
        time.sleep(0.25)
        source.write(":sour:swe:arm")
        time.sleep(3.0)
        
        np.savetxt(self.file, [np.insert(bias, 0, 0.0)], fmt = '%+.6e', delimiter = '\t')
        for gate in gates:
            print 'running IV for gate = {}V'.format(gate)
            daqGate.write([gate/gateAmp])
            time.sleep(gateDelay)
            data = np.array(source.execute_sweep(ivAvg = ivAvg, timeout = 120.0), dtype = np.floating)
            data = data*cvAmp #calculate current from voltage measurement
            for i in range(ivAvg): #save all data before averaging
                np.savetxt(self.file, [np.insert(data[i], 0, gate)], fmt = '%+.6e', delimiter = '\t')
                self.file.flush(); os.fsync(self.file)
                print data[i][0], data[i][1], '...', data[i][-2], data[i][-1] 
            data = data.mean(axis = 0) #average over multiple IV curves for plot
            
            if msvcrt.kbhit():
                if ord(msvcrt.getch()) == 113: #press 'q' to exit anytime
                    print "Program ended by user.\n"
                    break 

        print('Cleaning up...')
        source.write(":outp 0") #turn off current source
        source.close()
        daqGate.write([0.0]) #turn off gate
        del daqGate, source #delete DAQ object so it can be reused
        self.file.close()
            
    def run(self, *args, **kwargs):
    
        """ This will run the animation as the main thread and start a 
            second thread for the measurement.
            
            Takes all of the arguments and keyword arguments and passes them
            to self.run_simple """
        
        runArgs = args
        runKwargs = kwargs
        fileName = self.filename+'.dat'
        
        def update_iv_gate(num, fileName, title_text, line, ax):
            data = np.loadtxt(fileName, dtype = np.floating)
            line.set_ydata(data[-1,1:])
            ax.set_ylim(np.amin(data[-1,1:]), np.amax(data[-1,1:])) 
            title_text.set_text('gate = {}V'.format(data[-1,0]))
            return line, title_text
    
        t = Thread(target = self.run_simple, args = runArgs, kwargs = runKwargs)
        t.start()
        time.sleep(5.0)
        
        l = 0
        while l <2:
            data = np.loadtxt(fileName)
            l = len(np.shape(data))
            
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlim(np.amin(data[0,1:]), np.amax(data[0,1:]))
        ax.set_ylim(np.amin(data[-1,1:]), np.amax(data[-1,1:]))
        title_text = plt.title('gate = {}'.format(data[1, 0]))
        line, = ax.plot(data[0,1:], data[1,1:],'r-')
        plt.xlabel('bias')
        plt.ylabel('measured')

        line_ani = animation.FuncAnimation(fig, update_iv_gate, fargs=(fileName, title_text, line, ax),
            interval=1000, blit=False)

        plt.show()
        
if __name__ == "__main__":
    print 'Call the functions, fool!'
