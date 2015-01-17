""" A set of experiments to measure current as a function of several applied voltages
    These experiments all use the PCI-6259 DAQ and a current to voltage amplifier. """
    
from __future__ import division
import time, os, math
import msvcrt
import numpy as np
import matplotlib.pylab as plt
import matplotlib.animation as animation
import nidaqmx
import exptools as tools
from threading import Thread
    
class DAQIO_gateTest():

    """ Uses the DAQ to put out a bias voltage then sweeps the 
        back gate starting and ending at zero while measuring current with
        a current to voltage amplifier.
        
        This should be the safest way to measure the resistance of CNT samples
        at room temperature. """
        
    def __init__(self):
    
        """ This doesn't do much other than create the end_run variable. """

        self.end_run = False
        self.data = [0.0]
        
    def run_simple(self, bias, samples = 1.0, gateDelay = 0.75, field = 0.0, 
                   biasDivider = 1e-3, cvAmp = -1e-6, gateAmp = 9.1788, 
                   filename = 'DAQIO_gateTest_{0:.0f}'.format(time.time())):
        
        """ This runs the actual experiment. It can be called independently of the
            run() function. """
        
        tools.write_log('DAQIO_gateTest', locals(), filename+'.log.txt')
        file = open(filename+'.dat.txt','a')
        self.end_run = False
        
        #setup output channels
        bias_channel = 'Dev1/ao0'
        bias_out = nidaqmx.AnalogOutputTask()
        bias_out.create_voltage_channel(bias_channel, min_val = -10.0, max_val = 10.0)
        
        gate_channel = 'Dev1/ao1'
        gate_out = nidaqmx.AnalogOutputTask()
        gate_out.create_voltage_channel(gate_channel, min_val = -10.0, max_val = 10.0)
        
        gat = np.arange(0,10.1,0.1)
        gates = np.append(gat, [gat[::-1], -gat, -gat[::-1]])
        self.data = np.zeros((len(gates), samples+3))
        sample_data = np.zeros((samples,1))
        
        #setup input channel
        input_channel = 'Dev1/ai0' #if using differential mode this should be the high side
        sample_rate = 5000
        itask = nidaqmx.AnalogInputTask()
        itask.create_voltage_channel(input_channel, terminal = 'diff', min_val = -10.0, max_val = 10.0)
        itask.configure_timing_sample_clock(rate = sample_rate, samples_per_channel = samples, 
                                            sample_mode = 'finite')
        itask.alter_state('commit')
        
        print 'bias turning on...'
        bias_out.write(bias/biasDivider)
        time.sleep(10.0)

        #run experiment
        exitGate = 0.0
        print 'GO!'
        for i, gate in enumerate(gates):
            itask.start()
            gate_out.write(gate/gateAmp)
            time.sleep(gateDelay)
            sample_data = itask.read()
            itask.wait_until_done()
            itask.stop()
            self.data[i,0] = gate
            self.data[i,1] = sample_data.mean()*cvAmp
            self.data[i,2] = bias/self.data[i,1]
            self.data[i,3:] = sample_data.transpose()
            np.savetxt(file, [self.data[i]], fmt = '%+.6e', delimiter = '\t')
            if (msvcrt.kbhit() and ord(msvcrt.getch()) == 113) or self.end_run:
                    exitGate = gate
                    print "Program ended by user."
                    break
                
        bias_out.write(0.0)
        bias_out.clear()
        gate_out.write(0.0) #turn off gate, should already be at 0
        gate_out.clear()
        del gate_out, bias_out #delete DAQ object so it can be reused
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
        
        while np.count_nonzero(self.data[:,1]) < 3: 
            time.sleep(0.2)  #wait for at least three points to plot
            
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.grid(True)
        title_text = plt.title('bias = {0:+.2e}V'.format(args[0]))
        line, = ax.plot([], [],'r-o')
        plt.xlabel('gate (V)')
        plt.ylabel('current (A)')

        line_ani = animation.FuncAnimation(fig, update_current_gate, fargs=(line, ax),
            interval=1000, blit=False)
            
        plt.show()
        self.end_run = True
        
class DAQIO_stabilityTest():

    """ Uses the DAQ to put out a bias voltage then takes data at a few 
        back gate values while measuring current with
        a current to voltage amplifier.
        
        This should help in determining the problems with my gate setup. """
        
    def __init__(self):
    
        """ This doesn't do much other than create the end_run variable. """

        self.end_run = False
        self.data = 0.0
        
    def run_simple(self, bias, gateDelay = 1.0, measDelay = 0.75, 
                   field = 0.0, biasDivider = 1e-3, cvAmp = -1e-6, gateAmp = 9.1788, 
                   filename = 'DAQIO_gateTest_{0:.0f}'.format(time.time())):
        
        """ This runs the actual experiment. It can be called independently of the
            run() function. """
        
        tools.write_log('DAQIO_gateTest', locals(), filename+'.log.txt')
        file = open(filename+'.dat.txt','a')
        self.end_run = False
        
        sample_rate = 1000
        sample_average = 1000
        sample_number = 25
        
        #setup output channels
        bias_channel = 'Dev1/ao0'
        bias_out = nidaqmx.AnalogOutputTask()
        bias_out.create_voltage_channel(bias_channel, min_val = -10.0, max_val = 10.0)
        
        gate_channel = 'Dev1/ao1'
        gate_out = nidaqmx.AnalogOutputTask()
        gate_out.create_voltage_channel(gate_channel, min_val = -10.0, max_val = 10.0)
        
        gates = [0.0, 1.0, 0.0, -1.0, 0.0]
        # self.data = np.zeros((, ))
        # sample_data = np.zeros((sample_average,1))
        
        #setup input channel
        input_channel = 'Dev1/ai0' #if using differential mode this should be the high side
        itask = nidaqmx.AnalogInputTask()
        itask.create_voltage_channel(input_channel, terminal = 'diff', min_val = -5.0, max_val = 5.0)
        itask.configure_timing_sample_clock(rate = sample_rate, samples_per_channel = samples, 
                                            sample_mode = 'finite')
        itask.alter_state('commit')
        
        print 'bias turning on...'
        bias_out.write(bias/biasDivider)
        time.sleep(1.0)

        #run experiment
        exitGate = 0.0
        print 'GO!'
        for i, gate in enumerate(gates):
            gate_out.write(gate/gateAmp)
            time.sleep(gateDelay)
            for j in range(25):
                itask.start()
                sample_data = itask.read()
                itask.wait_until_done()
                itask.stop()
                
                self.data[i,0] = gate
                self.data[i,1] = sample_data.mean()*cvAmp
                self.data[i,2] = bias/self.data[i,1]
                self.data[i,3:] = sample_data.transpose()
                np.savetxt(file, [self.data[i]], fmt = '%+.6e', delimiter = '\t')
                if (msvcrt.kbhit() and ord(msvcrt.getch()) == 113) or self.end_run:
                        exitGate = gate
                        print "Program ended by user."
                        break
                
        bias_out.write(0.0)
        bias_out.clear()
        gate_out.write(0.0) #turn off gate, should already be at 0
        gate_out.clear()
        del gate_out, bias_out #delete DAQ object so it can be reused
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
        time.sleep(4.0)
        
        while np.count_nonzero(self.data[:,1]) < 3: 
            time.sleep(0.2)  #wait for at least three points to plot
            
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.grid(True)
        title_text = plt.title('bias = {0:+.2e}V'.format(args[0]))
        line, = ax.plot([], [],'r-o')
        plt.xlabel('gate (V)')
        plt.ylabel('current (A)')

        line_ani = animation.FuncAnimation(fig, update_current_gate, fargs=(line, ax),
            interval=1000, blit=False)
            
        plt.show()
        self.end_run = True
        
