""" This is a set of classes for different types of measurements utilizing the 
    Keithley 2182(A) nanovoltmeter. If it turns out that I only use one class in 
    here, this should be merged with instruments.py """
    
from __future__ import division
import time
import instruments #creates the source object
    
class SinglePoint(instruments.K2182): #takes the gpib address as an argument

    """ This will set up the nanovoltmeter to grab one averaged 
        measurement at a time. This class is a subclass of the 
        keithley 2182(A) class in instruments.py. That class is, 
        in turn, a subclass of visa.GpibInstrument. SinglePoint 
        inherits all of the functions of those two classes.
        Watch for the changes, try to keep up.

        Options: 1. 'bus trigger' fill the buffer with single points 
                    and read at the end, no immediate plotting
                 2. read single points directly with averaging
                    slower, immediate plotting """
        
    def general_setup(self, beep = False, display = True):

        """ reset and general commands to run before sweep setup:

            ':sour:swe:abor' -- abort previous sweep
            'RST;*CLS' -- reset and clear 6220
            '*RST;*CLS;:abor' -- reset, clear, abort previous 2182
            ':syst:beep:stat {}' -- turn off/on beep 6220+2182
            ':disp:enab {}' -- turn off/on the display 6220+2182 """
            
        self.write("*RST;*CLS;:abor")
        time.sleep(1.0)
        self.write(":syst:beep:stat {0:d}".format(beep))
        self.write(":disp:enab {0:d}".format(display))
        
    def trig_setup(self, trigSour, trigCoun, delay = 'auto'):

        """ setup commands for the nanovoltmeter trigger layer:

            ':trig:sour ext' -- external trigger
            ':trig:coun inf' -- infinite number of output triggers
            ':trig:del:auto on' -- turn on trigger auto delay, based on range
            delay time can also be specified manually 
            ':init:imm' -- initiate trigger layer """

        self.write(':trig:sour {}'.format(trigSour))
        self.write(':trig:coun {}'.format(trigCoun))
        if delay == 'auto':
            self.write(':trig:del:auto on')
        else:
            self.write(':trig:del:auto off')
            self.write(':trig:del {0:.3f}'.format(delay))
            
    def buffer_setup(self, bufferSize):

        """ setup commands for the nanovoltmeter buffer layer:

            ':trac:cle' -- clear buffer
            ':trac:feed sens1; poin {}' -- buffer to read channel 1/set size """

        self.write(":trac:cle") #clear buffer
        self.write(':trac:feed sens1')
        self.write('trac:poin {0:.0f}'.format(bufferSize))
        time.sleep(0.25)
        
    def bus_trig_setup(self, bufferSize):
    
        """ sets up the voltmeter buffer and trigger layers to take measurements
            when a *TRG signal is received and store them to the internal buffer.
            a usage example follows...
            
            general_setup(source)
            bias_setup(bias)
            voltmeter_channel_setup(*args)
            bus_trigger_setup()
            source.write('outp 1')
            
            for i in range(bufferSize):
                write_serial('*TRG')
            data = read_2182A_buffer() """
            
        self.trig_setup('bus', 'inf')
        self.write(":init:imm")
        self.buffer_setup(bufferSize)
    
    def get_avg_single(self):
    
        """ do not call this directly. it is used in the setup
            definition to define get_meas() """
            
        data = []
        for _ in range(self.avg):
            time.sleep(self.delay)
            data.append(float(self.ask('sens:data?')))
        return sum(data)/len(data)
            
    def get_avg_buffer(self):
    
        """ do not call this directly. it is used in the setup
            definition to define get_meas() """
            
        self.write('trac:feed:cont next') #this works
        while not self.chk_meas_evnt_reg()[9]: pass
        return self.ask('calc2:imm?')
    
    def single_point_setup(self, avg, delay):
    
        """ gets one measurement at a time, tries to optimize usage of the
            buffer. if avg = 1, this should be as fast as a single point
            measurement. a usage example follows...
            
            general_setup(source)
            bias_setup(bias)
            channel_setup(*args)
            single_point_setup(avg, delay)
            write('outp 1')
            
            for i in range(sweepSize):
                data[i] = get_meas()    
                
            make sure to call get_meas() not either of the get_avg_
            functions. """
        
        if avg < 10: #this cutoff is pretty accurate, based on a quick test
            self.trig_setup('imm', 'inf')
            self.avg = int(avg)
            self.delay = delay
            self.get_meas = self.get_avg_single
            
        elif avg > 1024:
            print 'don\'t be ridiculous.'
            raise RuntimeError('buffer is not that big!')
        
        else:
            self.trig_setup('imm', 'inf', delay)
            self.buffer_setup(avg)
            self.write(':calc2:form mean')
            self.write(':calc2:stat on')
            self.get_meas = self.get_avg_buffer
        self.write('init:imm')
