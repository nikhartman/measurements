======================
Transport Measurements
======================

Overview
========

    This set of Python scripts represent my first attempt at real-time data acquisition and plotting 
    with PyVISA and pylibnidaqmx. 

    The goal was to keep the plotting as simple as possible to facilitate easy writing of new experiment 
    classes. These measurements do work, but they aren't nearly as reliable as I'd like and adding additional 
    feedback forthe user quickly becomes very complicated. 

Structure
=========

    -instruments.py creates a class for each GPIB/RS232 device in our lab as a subclass of some PyVISA instrument 
    -specific instrument/measurement classes (e.g. nanovoltmeter.py). These create subclasses out of the instruments classes in instruments.py. The idea was to create a class for a specific type of measurement using that particular instrument (IV curve, differential conductance, ...). 
    -measurement classes (e.g. keithleypair_IV_swpVar.py) -- These classes/functions build specific experiments around the measurement classes defined for each instrument. 

Example
=======

    If I want to take several IV curves, each at a different magnetic field, using the Keithley 6220 and 2182A, 
    I can use keithleypair_IV_swpVar.IV_MagField(). This function uses instruemnts.oxford_magnet to control the 
    field and keithleypair.IVmax1024 (which is a subclass of instruments.K6220_2182A) to run an IV curve at each 
    magnetic field value.

    The experiment itself is written in the run_simple() function, which saves the data without attempting to 
    plot it. Plotting is possible through the run() function. This function calls run_simple() as a thread 
    while monitoring the class variable self.data and updating a plot with matplotlib.Animation

Dependencies
============

    *PyVISA -- http://pyvisa.sourceforge.net/
    *pylibnidaqmx -- https://code.google.com/p/pylibnidaqmx/
    *Numpy
    *matplotlib

Autor and Future Work
=====================

    This work was completed by Nik Hartman as a part of his PhD thesis in the Markovic lab at Johns Hopkins University.
    The author can be reached at: nhartman@pha.jhu.edu

    I'm interested in continuing this work, but it has reached a point that it has become too discracting from the main
    focus of my measurements. Any collaboration or comments are welcome. 
