""" A module to control various instruments in the lab using PyVISA.

    These instruments are instantiated with...
    my_instrument = instruments.name_of_instrument(gpib_identifier, *args)

    K6220_2182A   -- controls the Keithley 6220 source and 2182A voltmeter
                     assuming the source is connected through GPIB and the
                     voltmeter is connected to the 6220 over an RS232 port
                     and trigger link cable

    K2182         -- controls the Keithley 2182A nanovoltmeter when it is connected
                     directly through GPIB

    K6220         -- nothing yet.

    oxford_magnet -- controls the Oxford IPS 120-10 magnet power supply. the functions
                     are meant to keep the user from dealing with any of the strange
                     commands for this instrument.

    oxford_temp   -- controls the Oxford ITC503 temperature controler.
                     this is necessary to handle the strange read/write requirements
                     of that instrument. """

import visa
import time, math

class K6220_2182A(visa.GpibInstrument):

    """ Keithley 6220+2182A instrument class that inherits all of the functions of
    the visa.GpibInstrument class and adds some additional fucntionality for the
    serial port connection. """

    def nanovoltmeter_check(self):
        if int(self.ask(":sour:dcon:nvpr?")):
            print "2182A connected"
        else:
            raise RuntimeError('nanovoltmeter not found')

    def write_serial(self,message):

        """Sends a message to Keithley current source that is passed to
           voltmeter through a serial connection """

        self.write(":SYST:COMM:SER:SEND \"{}\"".format(message))
        time.sleep(0.1)

    def read_serial(self):

        """Reads data from 2182A through 6220"""

        self.write(":SYST:COMM:SER:ENT?")
        return self.read()

    def ask_serial(self,message):

        """A combination of write_serial(message) and read
           specific to Keithley current source and voltmeter"""

        self.write_serial(message)
        self.write(":SYST:COMM:SER:ENT?")
        return self.read()

    def test_command(self, instrument, command, compare):

        """ a function to send a string and compare to an expected result in
            order to test the connection to the equipment """
        result = ''
        try:
            if instrument == '6220':
                result = self.ask(command)
            elif instrument == '2182A':
                result = self.ask_serial(command)
            if result == compare:
                print "{0} has returned the value {1}, as expected.".format(command, result)
            else:
                raise RuntimeError("{0} has not been correctly set!"
                                   .format(command))
        except RuntimeError, err:
            print 'ERROR: {}'.format(err)

    def source_chk_op_evnt_reg(self):

        """ Checks the operational event register on the Keithley 6220
            Returns an array with the current status:
            B0 Calibrating
            B1 Sweep Done
            B2 Sweep Aborted
            B3 Sweeping
            B4 Wave Started
            B5 Waiting for Trigger Event
            B6 Waiting for Arm Event
            B7 Wave Stopped
            B8 Filter Settled
            B10 Idle State
            B11 RS-232 Error """

        state = int(self.ask(":STAT:OPER:EVEN?") )
        state = list('{0:016b}'.format(state))
        state.reverse()
        return [int(x) for x in state]

    def voltmeter_chk_meas_evnt_reg(self):

        """ Checks the measurement event register on the Keithley 2182
            through the serial bus of the 6220.
            Returns an array with the current status:
            B0 Reading Overflow
            B1 Low Limit 1
            B2 High Limit 1
            B3 Low Limit 2
            B4 High Limit 2
            B5 Reading Available?
            B7 At Least 2 Reading Stored in Buffer
            B8 Buffer Half Full
            B9 Buffer Full """

        state = int(self.ask_serial(":STAT:MEAS:COND?"))
        state = list('{0:016b}'.format(state))
        state.reverse()
        return [int(x) for x in state]

    def voltmeter_channel_setup(self, nplc = 1, vRange = 1.0, lp_filter = False,
                            digital_filter = False, filter_type = 'rep',
                            filter_count = 5, filter_window = 0.01):

        """ setup commands to measure voltage on channel 1:

            ':sens1:volt:nplc {}' -- measurement rate, nplc
            ':sens1:volt:rang:auto 0' -- turn off auto range
            ':sens1:volt:rang {}' -- set range in volts
            ':sens1:volt:lpas {}' -- low pass filter on/off
            ':sens1:volt:dfil {}' -- digital filter on/off
            ':sens1:volt:dfil:tcon {}; coun {}; wind {}' -- filter type/count/window 
            
            if you are sweeping over a large range, the digital filtering
            is very likely to ruin your day."""
        if vRange == 'auto':
            self.write_serial(':sens1:volt:rang:auto 1')
        else:
            self.write_serial(':sens1:volt:rang:auto 0')
            self.write_serial(':sens1:volt:rang {}'.format(vRange))
            self.write_serial(':sens1:volt:lpas {0:d}'.format(lp_filter))
        self.write_serial(':sens1:volt:nplc {}'.format(nplc))
        if digital_filter:
            self.write_serial(":sens1:volt:dfil {0:d}".format(digital_filter))
            self.write_serial(":sens1:volt:dfil:tcon {0}; coun {1:d}; wind {2:.2f}"
                                         .format(filter_type, int(filter_count), filter_window))
        else:
            self.write_serial(":sens1:volt:dfil {0:d}".format(digital_filter))
        time.sleep(0.25)

    def read_2182A_buffer(self, ignore = False):

        """ reads the voltmeter buffer after checking that it is not empty
            returns a list of strings as read from the voltmeter """

        if self.voltmeter_chk_meas_evnt_reg()[9] or ignore:
            pass
        else:
            filled = self.ask_serial(':trac:free?').split(',')[1]
            raise RuntimeError('buffer not full. points = {}'.format(float(filled)/18))
        buffer_points = int(self.ask_serial(":trac:points?"))
        loop_num = int(math.ceil(buffer_points*16.0/256.0))
        self.write_serial(":trac:data?")
        data = ''.join([self.ask(":syst:comm:ser:ent?") for _ in range(loop_num)])
        return data.split(',')

#    def fixed_bias(self, bias):
#
#        """ sets the 6220 to output a fixed bias """

class K2182(visa.GpibInstrument):

    """ This class handles the input/output from the Keithley 2182(A) nanovoltmeter
        when it is connected directly through GPIB """

    def chk_meas_evnt_reg(self):

        """ Checks the measurement event register on the Keithley 2182
            through the serial bus of the 6220.
            Returns an array with the current status:
            B0 Reading Overflow
            B1 Low Limit 1
            B2 High Limit 1
            B3 Low Limit 2
            B4 High Limit 2
            B5 Reading Available?
            B7 At Least 2 Reading Stored in Buffer
            B8 Buffer Half Full
            B9 Buffer Full """

        state = int(self.ask(":STAT:MEAS:COND?"))
        state = list('{0:016b}'.format(state))
        state.reverse()
        return [int(x) for x in state]

    def read_buffer(self):

        """ Reads the buffer and returns a list of strings.

            This works for ASCII data, but might need to be
            ammended for other data types. """

        data = self.ask(':trac:data?')
        return data.split(',')

    def channel_setup(self, nplc = 1, vRange = 1.0, lp_filter = False,
                            digital_filter = False, filter_type = 'rep',
                            filter_count = 5, filter_window = 0.01):

        """ setup commands to measure voltage on channel 1:

            ':sens1:volt:nplc {}' -- measurement rate, nplc
            ':sens1:volt:rang:auto 0' -- turn off auto range
            ':sens1:volt:rang {}' -- set range in volts
            ':sens1:volt:lpas {}' -- low pass filter on/off
            ':sens1:volt:dfil {}' -- digital filter on/off
            ':sens1:volt:dfil:tcon {}; coun {}; wind {}' -- filter type/count/window """

        self.write(":sens1:volt:nplc {0:f}".format(nplc))
        if vRange == 'auto':
            self.write(":sens1:volt:range:auto 1")
        else:
            self.write(":sens1:volt:rang:auto 0")
            self.write(":sens1:volt:rang {}".format(vRange))
        self.write(":sens1:volt:lpas {0:d}".format(lp_filter))
        if digital_filter:
            self.write(":sens1:volt:dfil {0:d}".format(digital_filter))
            self.write(":sens1:volt:dfil:tcon {0}; coun {1:d}; wind {2:.2f}"
                                         .format(filter_type, filter_count, filter_window))
        else:
            self.write(":sens1:volt:dfil {0:d}".format(digital_filter))
        time.sleep(0.25)

#class K2182(visa.GpibInstrument):

class oxford_magnet(visa.GpibInstrument):

    """ This class exists to handle the strange read/write requirements of the
        Oxford IPS120-10 magnet power supply 
        
        More functions will be added as soon as I figure out what I need. """

    err = 1e-6
        
    def __init__(self, gpib_identifier, rate = 0.2, **keyw):

        """ setup the read/write protocol:

           super( ... ) -- execute __init__ of interited GpibInstrument class
           b"/r" -- set term characheters to CR
           C3 -- set operation mode to remote with unlocked panel
           Q4 -- extended resolution mode
           M9 -- display field in Tesla
           H1 -- turn on switch heater and wait
           T{rate} -- set sweep rate
           A0 -- unclamp the power supply by going to hold and wait """

        super(oxford_magnet, self).__init__(gpib_identifier, **keyw)
        self.term_chars = b"\r"
        self.write("Q4")
        self.write("C3")
        self.read() #C
        self.write("M9")
        self.read() #M
        self.write("H1")
        self.read() #H
        print 'Waiting for switch heater (30s)...'
        time.sleep(30.0)
        self.write("T{:.5f}".format(rate)) #T... returns 'T'
        self.read() #T
        print 'Turning on hold...'
        time.sleep(0.5)
        self.write("A0") #A0 returns 'A'
        self.read() #A
        time.sleep(2.0)
        print 'Magnet is ready to use.'
        
    def set_rate(self, rate):
    
        """ change the rate from the value specified in __init__ """
        
        self.write('T{:.5f}'.format(rate))
        self.read() #T
        
    def go_to_field(self, field, delay = 0.0):

        """ Choose a set point and sweep the field to that value.
            Wait for confirmation that the field reached. 
           
            Resolution is 1e-5T. """
           
        if abs(float(self.ask('R7')[1:]) - field) <= self.err: 
            time.sleep(delay) #if it is already set, do nothing
        else:
            self.write('J{0:.5f}'.format(field))
            self.read() #J
            self.write('A1')
            self.read() #A
            while abs(float(self.ask('R7')[1:]) - field) >= self.err: pass
            time.sleep(delay)
            
    def end_at_zero(self):
        
        """ Sweep the field value back to 0T. Place magnet in hold
            position. 
            
            set field to zero
            set mode to Hold
            Turn off switch heater
            
            Useful to place at the end of an experiment. """
            
        self.go_to_field(0.0)
        time.sleep(2.0)
        self.write('A0')
        self.read() #A
        self.write('H0')
        self.read() #H

class oxford_temp(visa.GpibInstrument):

    """ This class exists to handle the strange read/write requirements of the
        Oxford ITC503 temperature controller """

    def __init__(self, gpib_identifier, **keyw):

       """ setup the read/write protocol:

           set term characheters to CR
           set feedback to normal (no LF)
           set operation mode to remote with unlocked panel """

       super(oxford_temp, self).__init__(gpib_identifier, **keyw)
       self.term_chars = b"\r"
       self.write("Q0")
       self.write("C3")
       self.read() #because write("C3") returns a 'C'

    def get_temps(self):
        """ get temperature readings in array """
        return [self.ask("R1")[1:], self.ask("R2")[1:], self.ask("R3")[1:]]

# To use the DAQ board there is no need yet for an additional class.
# See the pylibnidaqmx documentation for more. Here is a simple output example...

# import nidaqmx
# import numpy as np

# task = nidaqmx.AnalogOutputTask()
# task.create_voltage_channel('Dev1/ao0', min_val = -10.0, max_val = 10.0)
# voltages = np.arrange(-9.0,10.0,1.0)
# for volts in voltages
    # task.write([volts])
    # time.sleep(1.0)
# task.write([0.0])
# del task

# more complicated tasks may require the creation of a class here.
# alternately one can use the package PyDAQmx from the PyPI, but I haven't tried it