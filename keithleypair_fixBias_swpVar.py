""" This module contains functions for running experiments with Keithley
    6220/2182A to fix a current (voltage) bias and sweep a nidaq gate
    or magnetic field.
                 
    fixBias_swpGate_bustrig -- 6220 provides a bias current (voltage) while the nidaq 
                               sweeps a gate and the 2182 measures voltage (current).
                               This version is fast, but only plots at the end of a sweep.
                               This is meant to be used for taking a lot of data on samples
                               known to be working. There is no single point averaging, but 
                               the step size can be set very small and smoothed after the fact.
                 
    FixBias_SwpGate         -- 6220 provides a bias current (voltage) while the nidaq 
                               sweeps a gate and the 2182 measures voltage (current).
                               This version is slow, but provides realtime feedback
                               and averaging
    
    fixBias_swpField_bustrig-- same as fixBias_swpGate_bustrig except it sweeps a magnetic
                               field instead of a DAQ gate. 
                               
    fixBias_swpField         -- same as fixBias_swpGate except it sweeps a magnetic field
                               instead of a DAQ gate 
                               
    fixBias_swpTemp         -- the 6220 provides a bias current (voltage) while the 2182A
                               measures voltage (current) in realtime. This is meant to be
                               run during cool down/warm up 
                               
    Remember Atikur's gate amplifier has a gain of about 9.1788 """ 
    

from __future__ import division
import time, os, math
import msvcrt
import numpy as np
import matplotlib.pylab as plt
import matplotlib.animation as animation
import nidaqmx
import exptools as tools
import instruments
import keithleypair
from threading import Thread

class FixBias_SwpGate():

    """ Use the 6220 to fix a bias current(voltage) while sweeping the DAQ gate
        and measuring voltage(current) with the 2182A. Saves single points,
        no averaging, fastest way to plot something.
       
        If you are sourcing current and measuring voltage, set the cvAmp and
        cvResistor to 1.0
        
        gateLim should be arrays with 3 elements [start, stop, step] given in
        appropriate units (want to source voltage -- this should be volts). 
        
        The default behavior is to sweep one way, then the other, so as not to
        change the gate value too drastically.
        
        The field value is only there for logging purposes. If you want to run this
        sweep at a finite magnetic field, set the field manually and enter the
        appropriate value.
        
        Be sure to optimize the nanovoltmeter range. Setting it to 'auto' 
        is quite slow. """
        
    def __init__(self):
    
        """ This doesn't do much other than create the end_run variable. """

        self.end_run = False
        self.data = 0.0
        
    def run_simple(self, bias, gateLim, avg = 6.0, field = 0.0, runs = 1,
                   cvResistor = 1.0, cvAmp = 1.0, gateAmp = 9.1788, 
                   measDelay = 0.1, gateDelay = 1.0, nplc = 1, nvmRange = 0.1):
        
        """ This runs the actual experiment. It can be called independently of the
            run() function. """
        
        tools.write_log('fixBias_swpGate', locals(), self.filename+'.log')
        
        source = keithleypair.FixedBias("GPIB::22", timeout = 60.0) #keithley object
        daqGate = nidaqmx.AnalogOutputTask() #DAQ output object
        daqGate.create_voltage_channel('Dev1/ao0', min_val = -10.0, max_val = 10.0)
        
        gateBuffer = tools.get_buffer_size(gateLim[0], gateLim[1], gateLim[2])
        gates = np.linspace(gateLim[0], gateLim[1], gateBuffer)
        
        #setup 6220/2182A
        source.general_setup()
        source.bias_setup(bias/cvResistor)
        source.voltmeter_channel_setup(nplc, nvmRange)
        source.single_point_setup(avg, measDelay)
        
        #check that everything is setup
        print "current source state: ", source.source_chk_op_evnt_reg()
        print "voltmeter state:      ", source.voltmeter_chk_meas_evnt_reg()
        
        source.write(":outp 1")
        time.sleep(2.0)
        
        data = np.zeros(gateBuffer)

        for run in range(runs):
            end = False
            for i, gate in enumerate(gates):
                daqGate.write([gate/gateAmp])
                time.sleep(gateDelay)
                data[i] = source.get_meas()
                data[i] = data[i]*cvAmp
                np.savetxt(self.file, [[gate, data[i], run+1]], fmt = '%+.6e', delimiter = '\t')
                self.file.flush(); os.fsync(self.file)
                if msvcrt.kbhit():
                    if ord(msvcrt.getch()) == 113:
                        end = True
                        print "Program ended by user.\n"
                        break
            if end: break
            gates = gates.reshape(-1)[::-1]     #sweep in the other direction
            data.fill(0.0)
            
        print 'Cleaning up...'
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
        
        def update_current_gate(num, fileName, line, ax):
            data = np.loadtxt(fileName, dtype = np.floating)
            line.set_data(data[:,0], data[:,1])
            ax.set_xlim(np.amin(data[:,0]), np.amax(data[:,0]))
            ax.set_ylim(np.amin(data[:,1]), np.amax(data[:,1])) 
            return line, ax
    
        t = Thread(target = self.run_simple, args = runArgs, kwargs = runKwargs)
        t.start()
        time.sleep(3.0)
        
        p = 0
        while p <6:
            data = np.loadtxt(fileName, dtype = np.floating)
            p = np.size(data)  #wait for at least two points to plot
            
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.set_xlim(data[0,0], data[-1,0])
        ax.set_ylim(data[0,1]*0.9, data[-1,1]*1.1)
        title_text = plt.title('bias = {}V'.format(args[0]))
        line, = ax.plot(data[:,0], data[:,1],'r-o')
        plt.xlabel('gate')
        plt.ylabel('measured')

        line_ani = animation.FuncAnimation(fig, update_current_gate, fargs=(fileName, line, ax),
            interval=1000, blit=False)

        plt.show()

class FixBias_gateTest():

    """ Uses the 6220 to put out a bias voltage (current) then sweeps the 
        back gate starting and ending at zero while measuring current with
        a current to voltage amplifier and 2182.
        
        This should be the safest way to measure the resistance of CNT samples
        at room temperature. """
        
    def __init__(self):
    
        """ This doesn't do much other than create the end_run variable. """

        self.start_run = False
        self.end_run = False
        
    def run_simple(self, bias, avg = 1.0, field = 0.0, 
                   cvResistor = 10.0, cvAmp = -1e-7, gateAmp = 1.0, 
                   measDelay = 0.1, gateDelay = 0.75, nplc = 1, nvmRange = 1.0,
                   filename = 'roomTemp_cntTest_{0:.0f}'.format(time.time())):
        
        """ This runs the actual experiment. It can be called independently of the
            run() function. """
        
        tools.write_log('gateTest_vBias_', locals(), filename+'.log.txt')
        file = open(filename+'.dat.txt','a')
        
        self.end_run = False
        self.start_run = False
        
        source = keithleypair.FixedBias("GPIB::22", timeout = 60.0) #keithley object
        daqGate = nidaqmx.AnalogOutputTask() #DAQ output object
        daqGate.create_voltage_channel('Dev1/ao1', min_val = -10.0, max_val = 10.0)
        
        gat = np.arange(0,10.25,0.25)
        gates = np.append(gat, [gat[::-1], -gat, -gat[::-1]])
        self.data = np.zeros((len(gates), 3))
        
        #setup 6220/2182A
        source.general_setup()
        source.bias_setup(bias/cvResistor, analogFilt = False)
        source.voltmeter_channel_setup(nplc, nvmRange, digital_filter = False)
        source.single_point_setup(avg, measDelay)
        
        #check that everything is setup
        print "current source state: ", source.source_chk_op_evnt_reg()
        print "voltmeter state:      ", source.voltmeter_chk_meas_evnt_reg()
        
        #ramp up bias voltage
        if bias < 0: c = -1.0
        else: c = 1.0
        for i in range(-9, 0):
            outp = c*2*math.pow(10,i)
            if abs(outp) > abs(bias):  
                source.write(':sour:curr {0:.15f}'.format(bias/cvResistor))
                time.sleep(1.0)
                break
            else: 
                source.write(':sour:curr {0:.15f}'.format(outp/cvResistor))
                if i == -9:
                    source.write('outp 1')
                time.sleep(1.0)

        print 'wait for stable current...'; time.sleep(5.0)

        #run experiment
        exitGate = 0.0
        print 'GO!'
        for i, gate in enumerate(gates):
            daqGate.write(gate/gateAmp)
            time.sleep(gateDelay)
            self.data[i,0] = gate
            self.data[i,1] = source.get_meas()*cvAmp
            self.data[i,2] = bias/self.data[i,1]
            np.savetxt(file, [self.data[i]], fmt = '%+.6e', delimiter = '\t')
            if (msvcrt.kbhit() and ord(msvcrt.getch()) == 113) or self.end_run:
                    exitGate = gate
                    print "Program ended by user."
                    break
            if i == 2: self.start_run = True
        
        #ramp down bias voltage
        print 'Turning off bias...'
        for i in range(0, 10):
            outp = c*2*math.pow(10,-i)
            if abs(outp) > abs(bias): continue
            else: 
                source.write(':sour:curr {0:.15f}'.format(outp/cvResistor))
                time.sleep(1.0)
        
        #ramp down back gate
        print 'Turning off gate...'
        while True:
            if abs(exitGate) <1.0: break
            if exitGate < 0: exitGate += 1.0
            else: exitGate -= 1.0
            if abs(exitGate) < 1.0:
                break
            else:
                daqGate.write(exitGate/gateAmp)
                time.sleep(0.5)
                
        source.write(":outp 0") #turn off current source
        source.close() #close gpib instrument
        daqGate.write(0.0) #turn off gate, should already be at 0
        daqGate.clear()
        del daqGate, source #delete DAQ object so it can be reused
        file.close()
        print 'Done.'

    def run(self, *args, **kwargs):
    
        """ This will run the animation as the main thread and start a 
            second thread for the measurement.
            
            Takes all of the arguments and keyword arguments and passes them
            to self.run_simple """
        
        runArgs = args
        runKwargs = kwargs
        
        def update_current_gate(num, line, ax):
            poin = np.count_nonzero(self.data[:,1])
            line.set_data(self.data[0:poin,0], self.data[0:poin,1])
            ax.set_xlim(np.amin(self.data[0:poin,0]), np.amax(self.data[0:poin,0]))
            ax.set_ylim(np.amin(self.data[0:poin,1]),np.amax(self.data[0:poin,1])) 
            return line, ax
    
        t = Thread(target = self.run_simple, args = runArgs, kwargs = runKwargs)
        t.start()
        time.sleep(5.0)
        
        while self.start_run == False: time.sleep(0.2)
            
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.grid(True)
        title_text = plt.title('bias = {0:+.2e}V'.format(args[0]))
        line, = ax.plot([], [],'r-o')
        plt.xlabel('gate (V)')
        plt.ylabel('current (A)')

        line_ani = animation.FuncAnimation(fig, update_current_gate, fargs=(line, ax),
            interval=500, blit=False)

        plt.show()
        self.end_run = True
        
        
class FixBias_stabilityTest():

    """ Uses the 6220 to put out a bias voltage (current) the measures voltage
        as a function of time using the 2182A. Points are stored in the buffer
        and plotted at the end. """
        
    def __init__(self):
    
        """ This doesn't do much other than create the end_run variable. """

        self.start_run = False
        self.end_run = False
        
    def run(self, bias, points = 100, gateDelay = 0.75, 
                   cvResistor = 10.0, cvAmp = -1e-7, gateAmp = 1.0, 
                   nplc = 1, nvmRange = 1.0,
                   filename = 'roomTemp_cntTest_{0:.0f}'.format(time.time())):
        
        """ This runs the actual experiment. It can be called independently of the
            run() function. """
        
        tools.write_log('gateTest_vBias_', locals(), filename+'.log.txt')
        file = open(filename+'.dat.txt','a')
        
        self.end_run = False
        self.start_run = False
        
        source = keithleypair.FixedBias("GPIB::22", timeout = 60.0) #keithley object

        self.data = np.zeros((points, 4))
        
        #setup 6220/2182A
        source.general_setup()
        source.bias_setup(bias/cvResistor, analogFilt = True)
        source.voltmeter_channel_setup(nplc, nvmRange, digital_filter = False)
        source.bus_trig_setup(points)
        
        #check that everything is setup
        print "current source state: ", source.source_chk_op_evnt_reg()
        print "voltmeter state:      ", source.voltmeter_chk_meas_evnt_reg()
        
        #ramp up bias voltage
        if bias < 0: c = -1.0
        else: c = 1.0
        for i in range(-9, 0):
            outp = c*2*math.pow(10,i)
            if abs(outp) > abs(bias):  
                source.write(':sour:curr {0:.15f}'.format(bias/cvResistor))
                time.sleep(1.0)
                break
            else: 
                source.write(':sour:curr {0:.15f}'.format(outp/cvResistor))
                if i == -9:
                    source.write('outp 1')
                time.sleep(1.0)

        print 'wait for stable current...'; time.sleep(5.0)

        #run experiment
        print 'GO!'
        start_time = time.time()
        for i in range(points):
            time.sleep(gateDelay)
            source.write_serial('*TRG')
            self.data[i,0] = time.time() - start_time
            if (msvcrt.kbhit() and ord(msvcrt.getch()) == 113) or self.end_run:
                    print "Program ended by user."
                    break
        
        self.data[:,1] = source.read_2182A_buffer()
        self.data[:,2] = self.data[:,1]*cvAmp
        self.data[:,3] = bias/self.data[:,2]
        np.savetxt(file, self.data, fmt = '%+.6e', delimiter = '\t')
        
        #ramp down bias voltage
        print 'Turning off bias...'
        for i in range(0, 10):
            outp = c*2*math.pow(10,-i)
            if abs(outp) > abs(bias): continue
            else: 
                source.write(':sour:curr {0:.15f}'.format(outp/cvResistor))
                time.sleep(1.0)
                
        source.write(":outp 0") #turn off current source
        source.close() #close gpib instrument
        del source #delete DAQ object so it can be reused
        file.close()
        print 'Done.'
            
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.grid(True)
        title_text = plt.title('bias = {0:+.2e}V'.format(bias))
        line, = ax.plot(self.data[:,0], self.data[:,2],'r-o')
        plt.xlabel('time (s)')
        plt.ylabel('current (A)')
        plt.show()
        
        self.end_run = True
    
if __name__ == "__main__":
    print 'What you\'re doing is wrong.'
