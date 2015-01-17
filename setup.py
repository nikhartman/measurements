#!/usr/bin/evn python

from distutils.core import setup

setup(name = 'measurements'
      version = '1.0'
      description = 'transport measurements in the Markovic lab'
      author = 'Nik Hartman'
      author_email = 'nik.hartman@gmail.com'
      url = 'https://github.com/nikhartman/measurements'
      packages = ['', 'instruments', 'exptools']
      install_requires = ['pyvisa']

      # this also requires pylibnidaqmx, which is forked on my github page
      # in the correct version, but i'm not sure how to reference it here
      # this should be fixed if i ever have a reason to run this thing again
      
      #install_requires = ['pyvisa', 'PyLibNIDAQmx']
      #dependency_links = ['git+https://github.com/nikhartman/pylibnidaqmx']
