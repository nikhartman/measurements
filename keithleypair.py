""" this module contains useful functions to setup and
    execute measurements using the Keithley 6220 current source
    connected through GPIB with the 2182A nanovoltmeter connected
    to the 6220 through RS-232 and a trigger-link cable """

from __future__ import division
import time
import instruments #creates the source object
from exptools import buffer_split

class IVmax1024(instruments.K6220_2182A):

    """ A class of functions to setup and execute single IV curves.

    These function are meant to be called from your
    actual experiment scripts.

    Note: These IV curves are limited to 1024 points """
    
    def general_setup(self, beep = False, display = True):

        """ reset and general commands to run before sweep setup:

            ':sour:swe:abor' -- abort previous sweep
            'RST;*CLS' -- reset and clear 6220
            '*RST;*CLS;:abor' -- reset, clear, abort previous 2182
            ':syst:beep:stat {}' -- turn off/on beep 6220+2182
            ':disp:enab {}' -- turn off/on the display 6220+2182 """

        self.write(':sour:swe:abor')
        self.write('*RST;*CLS')
        time.sleep(1.0)
        self.nanovoltmeter_check()
        self.write_serial('*RST;*CLS;:abor')
        time.sleep(1.0)
        self.write(":syst:beep:stat {0:d}".format(beep))
        self.write_serial(":syst:beep:stat {0:d}".format(beep))
        self.write(":disp:enab {0:d}".format(display))
        self.write_serial(":disp:enab {0:d}".format(display))

    def source_sweep_setup(self, start, stop, step, delay, count = 1.0,
                           compliance = 100.0, compliance_abort = False):

        """ setup commands for the current source sweep:

            ':sour:swe:spac lin; rang {}; coun 1' -- spacing, range, number of sweeps
            ':sour:curr:start {}; stop {}; step {}' -- start, stop, step
            ':sour:del {}' -- source delay in seconds
            ':sour:curr:comp {0:f}' -- compliance voltage
            ':sour:swe:cab {0:d}' -- abort if compliance voltage is reached """
            
        #ranges = [2e-9, 2e-8, 2e-7, 2e-6, 2e-5, 2e-4, 0.002, 0.02, 0.1]
        
        self.write(':sour:swe:spac lin')
        #large = max(abs(stop), abs(start))
        #self.write(":sour:curr:rang {0:e}".format(filter(lambda range: range > large, ranges)[0]))
        self.write(':sour:swe:rang {0}'.format('best'))
        self.write(':sour:swe:coun {0:f}'.format(count))
        if start > stop:
            step = -step
        self.write(":sour:curr:start {0:e}; stop {1:e}; step {2:e}"
                             .format(start, stop, step))
        self.write(":sour:curr:comp {0:f}".format(compliance))
        self.write(":sour:swe:cab {0:d}".format(compliance_abort))
        self.write(":sour:del {0:.3f}".format(delay))
        #self.write(':sour:curr:filt:stat 1')

    def source_arm_setup(self):

        """ setup commands for the current source arm layer:

            ':arm:dir sour' -- control arm source bypaqss
            ':arm:sour bus' -- arm source set to serial bus
            ':arm:olin 2' -- output trigger from arm layer to pin 2
            ':arm:outp none' -- do not send output trigger from arm layer """

        self.write(':arm:dir acc') #sour or acc
        self.write(':arm:sour imm') #bus or imm
        self.write(':arm:olin 2') #output line 2 goes to the nvm
        self.write(':arm:outp none') #none, tex, or tent
        
    def source_trig_setup(self):

        """ setup commands for the current source trigger layer:

            ':trig:dir sour" -- source or acceptor, crucial!
            ':trig:sour tlin' -- set trigger source to trigger link cable
            ':trig:ilin 1; olin 2' -- set trigger link in/out pins
            ':trig:output del -- output trigger after source delay """
            
        self.write(':trig:sour tlin')
        self.write(':trig:dir sour')
        self.write(':trig:ilin 1; olin 2')
        self.write(':trig:outp del')

    def voltmeter_trig_setup(self, trigCoun = 'inf'):

        """ setup commands for the nanovoltmeter trigger layer:

            ':trig:sour ext' -- external trigger
            ':trig:coun inf' -- infinite number of output triggers
            ':trig:del:auto on' -- turn on trigger auto delay, based on range
            delay time can also be specified manually """

        self.write_serial(':trig:sour ext')
        #self.write_serial(':samp:coun {}'.format(sampCoun))
        self.write_serial(':trig:coun {}'.format(trigCoun))
        self.write_serial(':trig:del:auto on')
        time.sleep(0.25)

    def voltmeter_buffer_setup(self, buffer_size):

        """ setup commands for the nanovoltmeter buffer layer:

            ':trac:cle' -- clear buffer
            ':trac:feed sens1; poin {}' -- buffer to read channel 1/set size """
        
        self.write_serial(":trac:cle") 
        self.write_serial(":trac:feed sens1; poin {0:.0f}".format(buffer_size))
        time.sleep(0.25)

    def execute_sweep(self, ivAvg = 1, timeout = 75.0):

        """ this program will restart the buffer, trigger the sweep,
            and return the measured data for a given number of runs """

        data = []
        for iv in xrange(ivAvg):
            sweep_state = [0, 0, 1]
            self.write_serial(':trac:feed:cont next')
            time.sleep(0.25)
            self.write('syst:key 13')
            time.sleep(0.2)
            start_time = time.time()
            while ((time.time() - start_time) < timeout) and \
                  (not sweep_state[0]) and (not sweep_state[1]):
                sweep_state = self.source_chk_op_evnt_reg()[1:4]
            if (sweep_state[0]):
                print "{0}, execution time: {1:.2f}s".format(iv, time.time() - start_time)
            elif sweep_state[1]:
                raise RuntimeError('sweep aborted!')
            elif (time.time() - start_time) > timeout:
                raise RuntimeError('sweep timeout!')
            else:
                raise RuntimeError('sweep stopped for unknown reason?')
                
            time.sleep(1.0) #buffer fill delay
            data.append(self.read_2182A_buffer()) #this is not great
        return data
        
    # see keithleypair_IV_Var for usage examples
        
class IVunlim(instruments.K6220_2182A):

    """ A class of functions to setup and execute single IV curves.

    These function are meant to be called from your
    actual experiment scripts. Should be totally interchangable
    with IVmax1024. Might have to change the number of triggers
    from the 2182A to 'inf'

    Note: These IV curves are unlimited in length, but slightly 
          slower than the 1024 point option. """
          
    def general_setup(self, beep = False, display = True):

        """ reset and general commands to run before sweep setup:

            ':sour:swe:abor' -- abort previous sweep
            'RST;*CLS' -- reset and clear 6220
            '*RST;*CLS;:abor' -- reset, clear, abort previous 2182
            ':syst:beep:stat {}' -- turn off/on beep 6220+2182
            ':disp:enab {}' -- turn off/on the display 6220+2182 """

        self.write(":sour:swe:abor")
        self.write("*RST;*CLS")
        time.sleep(1.0)
        self.nanovoltmeter_check()
        self.write_serial("*RST;*CLS;:abor")
        time.sleep(1.0)
        self.write(":syst:beep:stat {0:d}".format(beep))
        self.write_serial(":syst:beep:stat {0:d}".format(beep))
        self.write(":disp:enab {0:d}".format(display))
        self.write_serial(":disp:enab {0:d}".format(display))

    def source_sweep_setup(self, start, stop, step, delay, count = 1.0,
                           compliance = 100.0, compliance_abort = False):

        """ setup commands for the current source sweep:

            ':sour:swe:spac lin; rang {}; coun 1' -- spacing, range, number of sweeps
            ':sour:curr:start {}; stop {}; step {}' -- start, stop, step
            ':sour:del {}' -- source delay in seconds
            ':sour:curr:comp {0:f}' -- compliance voltage
            ':sour:swe:cab {0:d}' -- abort if compliance voltage is reached """
            
        ranges = [2e-9, 2e-8, 2e-7, 2e-6, 2e-5, 2e-4, 0.002, 0.02, 0.1]
        
        self.write(':sour:swe:spac lin')
        large = max(abs(stop), abs(start))
        self.write(":sour:curr:rang {0:e}".format(filter(lambda range: range > large, ranges)[0]))
        self.write(':sour:swe:rang {0}'.format('fix'))
        self.write(':sour:swe:coun {0:f}'.format(count))
        if start > stop:
            step = -step
        self.write(":sour:curr:start {0:e}; stop {1:e}; step {2:e}"
                             .format(start, stop, step))
        self.write(":sour:del {0:.3f}".format(delay))
        self.write(":sour:curr:comp {0:f}".format(compliance))
        self.write(":sour:swe:cab {0:d}".format(compliance_abort))
        self.write(':sour:curr:filt:stat 1') #makes no noticable time difference
        time.sleep(0.5)

    def source_arm_setup(self):

        """ setup commands for the current source arm layer:

            ':arm:dir sour' -- control arm source bypaqss
            ':arm:sour bus' -- arm source set to serial bus
            ':arm:olin 2' -- output trigger from arm layer to pin 2
            ':arm:outp none' -- do not send output trigger from arm layer """

        self.write(':arm:dir sour') #sour or acc
        self.write(':arm:sour imm') #bus or imm
        self.write(':arm:olin 2') #output line 2 goes to the nvm
        self.write(':arm:outp none') #none, tex, or tent
        time.sleep(0.5)

    def source_trig_setup(self):

        """ setup commands for the current source trigger layer:

            ':trig:dir sour" -- source or acceptor, crucial!
            ':trig:sour tlin' -- set trigger source to trigger link cable
            ':trig:ilin 1; olin 2' -- set trigger link in/out pins
            ':trig:output del -- output trigger after source delay """

        self.write(":trig:dir sour")
        self.write(":trig:sour tlin")
        self.write(":trig:ilin 1; olin 2")
        self.write(":trig:outp none")
        time.sleep(0.5)

    def voltmeter_trig_setup(self, trigCoun = 'inf'):

        """ setup commands for the nanovoltmeter trigger layer:

            ':trig:sour ext' -- external trigger
            ':trig:coun inf' -- infinite number of output triggers
            ':trig:del:auto on' -- turn on trigger auto delay, based on range
            delay time can also be specified manually """

        self.write_serial(':trig:sour bus')
        #self.write_serial(':samp:coun {}'.format(sampCoun))
        self.write_serial(':trig:coun {}'.format(trigCoun))
        self.write_serial(':trig:del:auto on')
        self.write_serial(':init:imm')

    def voltmeter_buffer_setup(self, buffer_size):

        """ setup commands for the nanovoltmeter buffer layer:

            ':trac:cle' -- clear buffer
            ':trac:feed sens1; poin {}' -- buffer to read channel 1/set size """

        self.write_serial(":trac:cle") 
        self.bufferRuns, self.bufferSize = buffer_split(buffer_size)
        self.write_serial(":trac:feed sens1; poin {0:.0f}".format(self.bufferSize))
        time.sleep(0.25)

    def execute_sweep(self, ivAvg = 1, delay = 0.2, timeout = 75.0):
                      
        """ this program will restart the buffer, trigger the sweep,
            and return the measured data for a given number of runs """

        data = []
        ivData = [0.0 for _ in range(self.bufferRuns*self.bufferSize)]
        for iv in range(ivAvg):
            start_time = time.time()
            self.write(':init:imm')
            for run in range(self.bufferRuns):
                self.write_serial(':trac:feed:cont next')
                for i in range(self.bufferSize):
                    time.sleep(delay)
                    self.write_serial('*TRG')
        
                time.sleep(1.0) #buffer fill delay
                ivData[run:(run+1)*self.bufferSize] = self.read_2182A_buffer()
            print "{0}, execution time: {1:.2f}s".format(iv, time.time() - start_time)
            data.append(ivData) #this is not great
        return data

class FixedBias(instruments.K6220_2182A): #takes a gpib address as an argument

    """ A class of functions to setup the 6220/2182A to output a
        fixed bias and measure voltage on command.  This class is
        a subclass of the keithley K6220_2182A class in instruments.py
        That class is, in turn, a subclass of visa.GpibInstrument
        FixedBias inherits all of the functions of those two classes.
        Watch for the changes, try to keep up.

        Options: 1. fill the buffer with single points and read
                    fast, no immediate plotting
                 2. read single points directly with averaging
                    slower, immediate plotting is possible """
        
    def general_setup(self, beep = False, display = True):

        """ reset and general commands to run before sweep setup:

            ':sour:swe:abor' -- abort previous sweep
            'RST;*CLS' -- reset and clear 6220
            '*RST;*CLS;:abor' -- reset, clear, abort previous 2182
            ':syst:beep:stat {}' -- turn off/on beep 6220+2182
            ':disp:enab {}' -- turn off/on the display 6220+2182 """
            
        self.write(":sour:swe:abor")
        self.write("*RST;*CLS")
        self.nanovoltmeter_check()
        time.sleep(1.0)
        self.write_serial("*RST;*CLS;:abor")
        time.sleep(1.0)
        self.write(":syst:beep:stat {0:d}".format(beep))
        self.write_serial(":syst:beep:stat {0:d}".format(beep))
        self.write(":disp:enab {0:d}".format(display))
        self.write_serial(":disp:enab {0:d}".format(display))
        
    def bias_setup(self, bias, autoRange = False,
                   compliance = 100.0, compliance_abort = False, 
                   analogFilt = True):
                   
        """ setup fixed bias output on 6220 
        
            ":sour:curr:rang:auto off' -- turn off auto range
            ':sour:curr:rang {0:e}' -- set manual range
            ':sour:curr {0.15f}' -- set bias 
            ':sour:curr:comp {0:e}' -- set compliance voltage
            ':sour:curr:filt:stat {0:d}' -- abort on compliance? """
        if autoRange:
            self.write('sour:curr:range:auto on')
        else:
            ranges = [2e-9, 2e-8, 2e-7, 2e-6, 2e-5, 2e-4, 0.002, 0.02, 0.1]
            self.write(":sour:curr:rang:auto off")
            self.write(":sour:curr:rang {0:e}".format(filter(lambda range: range > abs(bias), ranges)[0]))
            
        self.write(":sour:curr {0:.15f}".format(bias))
        self.write(":sour:curr:comp {0:e}".format(compliance))
        self.write(":sour:curr:filt:stat {0:d}".format(analogFilt))
        
    def voltmeter_trig_setup(self, trigSour, trigCoun, delay = 'auto'):

        """ setup commands for the nanovoltmeter trigger layer:

            ':trig:sour ext' -- external trigger
            ':trig:coun inf' -- infinite number of output triggers
            ':trig:del:auto on' -- turn on trigger auto delay, based on range
            delay time can also be specified manually 
            ':init:imm' -- initiate trigger layer """

        self.write_serial(':trig:sour {}'.format(trigSour))
        self.write_serial(':trig:coun {}'.format(trigCoun))
        if delay == 'auto':
            self.write_serial(':trig:del:auto on')
        else:
            self.write_serial(':trig:del:auto off')
            self.write_serial(':trig:del {0:.3f}'.format(delay))
            
    def voltmeter_buffer_setup(self, bufferSize):

        """ setup commands for the nanovoltmeter buffer layer:

            ':trac:cle' -- clear buffer
            ':trac:feed sens1; poin {}' -- buffer to read channel 1/set size """

        self.write_serial(":trac:cle") #clear buffer
        self.write_serial(':trac:feed sens1')
        self.write_serial('trac:poin {0:.0f}'.format(bufferSize))
        time.sleep(0.25)
        
    def bus_trig_setup(self, bufferSize):
    
        """ sets up the voltmeter buffer and trigger layers to take measurements
            when a *TRG signal is received and store them to the internal buffer.
            a usage example follows...
            
            general_setup()
            bias_setup(bias)
            voltmeter_channel_setup(*args)
            bus_trigger_setup()
            source.write('outp 1')
            
            for i in range(bufferSize):
                write_serial('*TRG')
            data = read_2182A_buffer() """
            
        self.voltmeter_trig_setup('bus', 'inf')
        self.voltmeter_buffer_setup(bufferSize)
        self.write_serial('trac:feed:cont next')
        self.write_serial(':init:imm')
    
    def get_avg_single(self):
    
        """ do not call this directly. it is used in the setup
            definition to define get_meas() """
            
        data = []
        for _ in range(self.avg):
            time.sleep(self.delay)
            data.append(float(self.ask_serial('sens:data?')))
        return sum(data)/len(data)
            
    def get_avg_buffer(self):
    
        """ do not call this directly. it is used in the setup
            definition to define get_meas() """
            
        self.write_serial('trac:feed:cont next') #this works
        while not self.voltmeter_chk_meas_evnt_reg()[9]: pass
        self.write_serial('calc2:imm?')
        time.sleep(0.01)
        return float(self.read_serial())
    
    def single_point_setup(self, avg, delay):
    
        """ gets one measurement at a time, tries to optimize usage of the
            buffer. if avg = 1, this should be as fast as a single point
            measurement. a usage example follows...
            
            general_setup(source)
            bias_setup(bias)
            voltmeter_channel_setup(*args)
            single_point_setup(avg, delay)
            write('outp 1')
            
            for i in range(sweepSize):
                data[i] = get_meas()    
                
            make sure to call get_meas() not either of the get_avg_
            functions. """
        
        if avg < 6: #this cutoff is pretty accurate, based on a quick test
            self.voltmeter_trig_setup('imm', 'inf')
            self.avg = int(avg)
            self.delay = delay
            self.get_meas = self.get_avg_single
            
        elif avg > 1024:
            print 'don\'t be ridiculous.'
            raise RuntimeError('buffer is not that big!')
        
        else:
            self.voltmeter_trig_setup('imm', 'inf', delay)
            self.voltmeter_buffer_setup(avg)
            self.write_serial(':calc2:form mean')
            self.write_serial(':calc2:stat on')
            self.get_meas = self.get_avg_buffer
        self.write_serial('init:imm')
        
    # def _test_(source, bias, nplc = 1.0, nvmRange = 0.1)
       
        # """ this is just meant to be an example of how to use the functions in this
            # class to setup a measurement. """
        
        # source = instruments.K6220_2182A("GPIB::22", timeout = 60.0) #keithley object
        # daqGate = nidaqmx.AnalogOutputTask() 
        # daqGate.create_analog_voltage_channel('Dev1/ao0', min_val = -10.0, max_val = 10.0)
        
        # gateBuffer = tools.get_buffer_size(gateLim[0], gateLim[1], gateLim[2])
        # fill, points = tools.buffer_split(gateBuffer) #important if gateBuffer>1024
        # gates = np.linspace(gateLim[0], gateLim[1], gateBuffer)
        
        # FixedBias.general_setup(source)
        # FixedBias.bias_setup(source, bias)
        # source.voltmeter_channel_setup(nplc, nvmRange)
        # FixedBias.voltmeter_trig_setup(source)
        # FixedBias.voltmeter_buffer_setup(source)
        # source.write(":outp 1")
        
        # data = np.zeros(gateBuffer)
        # gates = gates.reshape(fill, points) #resize if multiple reads are needed
        # for i, row in enumerate(gates):
            # source.write_serial(":trac:feed:cont next")
            # for gate in row:
                # daqGate.write(gate/gateAmp)
                # time.sleep(gateDelay)
                # source.write_serial("*TRG")
            # data[i*points:(i+1)*points] = np.array(source.read_2182A_buffer())
        # np.savetxt(file, [np.insert(data, 0, run+1)], fmt = '%+.6e', delimiter = '\t')
        
if __name__ == "__main__":
    print 'you probably shouldn\'t do this.'
