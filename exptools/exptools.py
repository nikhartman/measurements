""" This module is a set of useful tools for my measurements
    that don't seem to have another home. """

import time
import math
    
def write_log(func, arguments, filename):
    
    """ A function to log the arguments sent to a fucntion to 
        a log file. I'm putting it here because I import this module
        to all my experiments. Should look something like this...
        
        write_log(locals(), filename+'.log') 
        
        More notes can be added after the fact. This is just a fast
        way to dump all of the variables at once. """
        
    print filename
    file = open(filename, 'w')
    file.write('function: {}\n'.format(func))
    file.write('time of call: {}\n'.format(time.asctime()))
    file.write('\n')
    for arg, value in arguments.items():
        file.write('{0} = {1}\n'.format(arg, value))
    file.close()
    
def get_buffer_size(start, stop, step):

    """ calculate the necessary buffer size given the
        start stop and step values
        
        this may not always match the keithley calculation.
        I don't understand why. """
        
    buffer_size = abs((start - stop)/step)
    if float(buffer_size % 1) >= 0.5:
        return math.floor(buffer_size)+2
    else:
        return math.floor(buffer_size)+1
        
def buffer_split(points):
    
    """ The buffer on the 2182 nanovoltmeter is limited to 
        1024 points. This function splits an arbitrary number
        of points into appropriately sized chunks. It returns
        the number of chunks and their length. """
    
    i = 1024
    if points < 1025:
        return (1, int(points))
    else: 
        while (i > 99) and (not points%i == 0):
            i-=1
        if i != 99:
            return (int(points/i), int(i))
        else:
             raise RuntimeError('There are no factors of {} < 1024 and > 99'
                                   .format(points))
