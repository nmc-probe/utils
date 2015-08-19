# Copyright (c) 2015 The New Mexico Consortium
# 
# {{{NMC-LICENSE
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS
# OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#
# }}}

import os
from nmc_probe.log import Log
from nmc_probe.command import Command, AsynchronousFileReader
import subprocess, threading, time, Queue
from nmc_probe.bladeutilsconfig import BladeUtilsConfig

class SNMP:
    """
    Handle SNMP requests destined for a particular host
    """
    def __init__(self, host, version, readCommunity, writeCommunity = None):
        """
        Constructor
        
        Params
        -----
        host      : string
                    The IP address or hostname to which requests will be made
        version   : int
                    SNMP version to use
        community : string
                    The read-only community
        """
        self.host = host
        self.version = version
        self.readCommunity = readCommunity

        if writeCommunity:
            self.writeCommunity = writeCommunity

    @classmethod
    def withConfigFile(cls, host, file = None):
        config = None

        if file:
            config = BladeUtilsConfig(file)
        else:
            config = BladeUtilsConfig()

        os.environ['MIBS'] = config.options['snmp']['mibs']

        return cls(host,
                   config.options['snmp']['version'],
                   config.options['snmp']['get'],
                   config.options['snmp']['set'])
        

    def parseSNMPLine(self, line):
        """
        Private member, parses a line of output from snmpwalk

        Returns
        -------
        A tuple (oid, value)
        """
        oid = None
        value = None
        # Split the line on the first '=' character
        parts = line.split('=', 1)
        if len(parts) == 2:
            oid = parts[0].rstrip().lstrip()
            value = parts[1].rstrip().lstrip()

            valueParts = value.split(':', 1)

            if len(valueParts) == 2:
                type = valueParts[0].rstrip().lstrip()
                value = valueParts[1].rstrip().lstrip()

                if type == 'STRING':
                    value = value.rstrip('"').lstrip('"')
            else:
                Log.error('Cannot parse SNMP value: "%s"' % (valueType))
        else:
            Log.error('Cannot parse SNMP key/value pair: "%s"' % (line))

        return (oid, value)

    def extractLastOctet(self, oid):
        """
        Returns
        -------
        The last octect from an oid
        """
        parts = oid.split('.')
        if len(parts) > 0:
            return parts[-1]
        return None

    def extractOidBaseAndLastOctet(self, oid):
        """
        Helper function for extractOidParts
        """
        # Split the OID on the last occurrence of '.'
        oidParts = oid.rsplit('.', 1)

        oidBase = None
        lastOctet = None

        if len(oidParts) == 2:
            # OID has the format: stuff.N
            oidBase = oidParts[0]
            lastOctet = oidParts[1]
        elif len(oidParts) == 1:
            oidBase = oidParts[0]

        return (oidBase, lastOctet)

    def extractOidParts(self, oid):
        """
        Returns:
        --------
        A 3-tuple: (MIB name, oid base, last octet). Examples of return values

        DISMAN-EVENT-MIB::sysUpTimeInstance -> ('DISMAN-EVENT-MIB', 'sysUpTimeInstance', None)
        .1.3.6.1.2.1.1.3.0                  -> (None, '.1.3.6.1.2.1.1.3', '0')
        SNMPv2-MIB::snmpOutGetResponses.0   -> (SNMPv2-MIB, 'snmpOutGetResponses', '0)
        """

        # Split on ::, but just the first instance of ::. There should be only one 
        # set of double colons, but let's be specific about our intentions
        parts = oid.split('::', 1)

        mibName = None
        oidBase = None
        lastOctet = None

        if len(parts) == 2:
            # This oid has the format MIB-NAME::other_stuff
            mibName = parts[0]
            oidBase = parts[1]

            (oidBase, lastOctet) = self.extractOidBaseAndLastOctet(oidBase)
        else:
            (oidBase, lastOctet) = self.extractOidBaseAndLastOctet(oid)
            
        return (mibName, oidBase, lastOctet)

    def walk(self, oid):
        """
        Perform an SNMP walk

        Params
        -----
        oid : string
              The starting OID
        """
        version = '-v1'
        if self.version == 2:
            version = '-v2'

        args = ['/usr/bin/snmpwalk', '-t', '120', version, '-c', self.readCommunity, self.host, oid]
        Log.debug(100, ' '.join(args))
        (output, exitcode) = Command.run(args)

        values = None
        if exitcode == 0 and output:
            values = []
            for line in output:
                line.rstrip('\n')
                if len(line) > 0:
                    values.append(self.parseSNMPLine(line))

        return values

    def set(self, oid, oidType, value):
        """
        Perform an SNMP set
        """
        version = '-v1'
        if self.version == 2:
            version = '-v2'

        args = ['/usr/bin/snmpset', '-t', '120', version, '-c', self.writeCommunity, self.host, oid, oidType, value]
        return  Command.run(args)

class SNMPWalk(threading.Thread):
    """
    Handle SNMP requests destined for a particular host
    """
    def __init__(self, host, version, readCommunity, oid):
        """
        Constructor
        
        Params
        -----
        host      : string
                    The IP address or hostname to which requests will be made
        version   : int
                    SNMP version to use
        community : string
                    The read-only community
        """
        self.host = host
        self.version = version
        self.readCommunity = readCommunity
        self.oid = oid
        self.queue = Queue.Queue()
        threading.Thread.__init__(self)
        self.start()

    @classmethod
    def withConfigFile(cls, host, oid, file = None):
        config = None

        if file:
            config = BladeUtilsConfig(file)
        else:
            config = BladeUtilsConfig()

        return cls(host,
                   config.options['snmp']['version'],
                   config.options['snmp']['get'],
                   oid)

    def run(self):
        """
        Perform an SNMP walk
        """
        version = '-v1'
        if self.version == 2:
            version = '-v2'

        command = ['/usr/bin/snmpwalk', '-t', '120', version, '-c', self.readCommunity, self.host, self.oid]
        Log.debug(100, ' '.join(command))

        # Launch the command as subprocess.
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
 
        # Launch the asynchronous readers of the process' stdout and stderr.
        stdoutQueue = Queue.Queue()
        stdoutReader = AsynchronousFileReader(process.stdout, stdoutQueue)
        stdoutReader.start()
        stderrQueue = Queue.Queue()
        stderrReader = AsynchronousFileReader(process.stderr, stderrQueue)
        stderrReader.start()

        # Check the queues if we received some output (until there is nothing more to get).
        while not stdoutReader.eof() or not stderrReader.eof():
            # Show what we received from standard output.
            while not stdoutQueue.empty():
                line = stdoutQueue.get()
                self.queue.put(self.split(line))
 
            # Show what we received from standard error.
            while not stderrQueue.empty():
                line = stderrQueue.get()
                print 'Received line on standard error: ' + repr(line)
 
            # Sleep a bit before asking the readers again.
            time.sleep(.1)
 
        # Let's be tidy and join the threads we've started.
        stdoutReader.join()
        stderrReader.join()
 
        # Close subprocess' file descriptors.
        process.stdout.close()
        process.stderr.close()

    @property
    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive() and self.queue.empty()

    def split(self, line):
        """
        Private member, splits a line of snmpwalk output into the oid and value

        Returns
        -------
        A tuple (oid, value)
        """
        oid = None
        value = None

        # Split the line on the first '=' character
        parts = line.split('=', 1)
        if len(parts) == 2:
            oid = parts[0].rstrip().lstrip()
            value = parts[1].rstrip().lstrip()

            valueParts = value.split(':', 1)

            if len(valueParts) == 2:
                type = valueParts[0].rstrip().lstrip()
                value = valueParts[1].rstrip().lstrip()

                if type == 'STRING':
                    value = value.rstrip('"').lstrip('"')
            else:
                Log.error('Cannot parse SNMP value: "%s"' % (valueType))
        else:
            Log.error('Cannot parse SNMP key/value pair: "%s"' % (line))

        return (oid, value)

    def extractLastOctet(self, oid):
        """
        Returns
        -------
        The last octect from an oid
        """
        parts = oid.split('.')
        if len(parts) > 0:
            return parts[-1]
        return None

    def extractOidBaseAndLastOctet(self, oid):
        """
        Helper function for extractOidParts
        """
        # Split the OID on the last occurrence of '.'
        oidParts = oid.rsplit('.', 1)

        oidBase = None
        lastOctet = None

        if len(oidParts) == 2:
            # OID has the format: stuff.N
            oidBase = oidParts[0]
            lastOctet = oidParts[1]
        elif len(oidParts) == 1:
            oidBase = oidParts[0]

        return (oidBase, lastOctet)

    def extractOidParts(self, oid):
        """
        Returns:
        --------
        A 3-tuple: (MIB name, oid base, last octet). Examples of return values

        DISMAN-EVENT-MIB::sysUpTimeInstance -> ('DISMAN-EVENT-MIB', 'sysUpTimeInstance', None)
        .1.3.6.1.2.1.1.3.0                  -> (None, '.1.3.6.1.2.1.1.3', '0')
        SNMPv2-MIB::snmpOutGetResponses.0   -> (SNMPv2-MIB, 'snmpOutGetResponses', '0)
        """

        # Split on ::, but just the first instance of ::. There should be only one 
        # set of double colons, but let's be specific about our intentions
        parts = oid.split('::', 1)

        mibName = None
        oidBase = None
        lastOctet = None

        if len(parts) == 2:
            # This oid has the format MIB-NAME::other_stuff
            mibName = parts[0]
            oidBase = parts[1]

            (oidBase, lastOctet) = self.extractOidBaseAndLastOctet(oidBase)
        else:
            (oidBase, lastOctet) = self.extractOidBaseAndLastOctet(oid)
            
        return (mibName, oidBase, lastOctet)
