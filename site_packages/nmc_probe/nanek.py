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

import re,bitarray,datetime,uuid,sys
from nmc_probe.couchdb import CouchDoc
from nmc_probe.log import Log
from nmc_probe.command import Command
from nmc_probe.snmp import SNMP, SNMPWalk
from bitarray import bitarray

class Blade (CouchDoc):
    """
    Defines a blade for use in IBM BladeCenter H,
    specifically for the NMC's Nanek cluster and
    similar mini-clusters.

    This class is designed to persist itself to
    CouchDB
    
    Attributes
    ----------
    docId
    persistentAttributes
    type
    mac0         : string
                   mac address for eth0
    mac1         : string
                   mac address for eth1
    biosVersion  : string
                   bios version
    diagVersion  : string
                   on board diagnostics version
    bmcVersion   : string
                   system processor / baseboard management console version
    serialNumber : string
                   The serial number for this blade
    """
    @property
    def type(self):
        """
        Returns:
        -------
        A text representation of the type of object. Stored
        as the type attribute in Couch
        """
        return 'blade'

    @property
    def docId(self):
        """
        Returns
        -------
        string
            The unique document ID for this object used by CouchDB
        """
        return self.mac0

    @property
    def persistentAttributes(self):
        """
        Returns
        -------
            An array attributes that will be persisted to CouchDB
        """
        return ['mac0', 'mac1', 'biosVersion',
                'bmcVersion', 'diagVersion', 'serialNumber',
                'memory', 'numCPUs', 'incorrectBIOSSettings',
                'healthState']

    @property
    def mac0(self):
        return self.__mac0

    @mac0.setter
    def mac0(self, value):
        self.__mac0 = value.lower()

    @property
    def mac1(self):
        return self.__mac1

    @property
    def validMac0(self):
        return self.isValidMac(self.mac0)

    @mac1.setter
    def mac1(self, value):
        self.__mac1 = value.lower()

    @classmethod
    def discoverNumCPUs(self):
        '''
        Checks /proc/cpuinfo for the number of processors
        '''
        (lines, exitcode) = Command.run(['/bin/cat', '/proc/cpuinfo'])
        regex = re.compile('^processor\s+:')
        return len(filter(regex.match, lines))

    @classmethod
    def discoverMemory(self):
        '''
        Returns the amount of physical memory on this computer
        '''
        (lines, exitcode) = Command.run(['free'])
        regex = re.compile('^Mem:\s+')
        memLine = filter(regex.match, lines)
        memLineParts = memLine[0].split()
        return memLineParts[1]

    @classmethod
    def discoverMac0(self):
        '''
        Returns the mac address of eth0
        '''
        (output, exitcode) = Command.run(['/sbin/ip', 'addr', 'show', 'eth0'])
        regex = re.compile('^\s+link\/ether')
        filteredLines = filter(regex.match, output)
        firstLineSplit = filteredLines[0].split()
        return firstLineSplit[1]

    @classmethod
    def discoverIncorrectBIOSSettings(cls, expectedFilename, dumpCmd):
        """
        Discover incorrect BIOS settings
        
        Params
        ------
        expectedFilename: string
        A filename of expected bios settings

        dumpCmd: array
        Command to dump bios settings

        Returns
        A dictionary of key value pairs of incorrect bios settings
        """

        try:
            # Read expected bios settings
            expectedFile = Blade.openFile(expectedFilename)
            expected = Blade.parseBios(expectedFile)

            # Read actual bios settings
            (actualFile, exitcode) = Command.run(dumpCmd)
            actual = Blade.parseBios(actualFile)

            return Blade.compareBiosSettings(expected, actual)
        except (OSError, IOError) as e:
            Log.error(str(e))
            sys.exit(1)

        return None

    @classmethod
    def compareBiosSettings(cls, expected, actual):
        incorrectSettings = {}
        for key in expected:
            if actual.has_key(key):
                if not expected[key] == actual[key]:
                    incorrectSettings[key] = {"expected": expected[key],
                                              "actual":   actual[key]}

        return incorrectSettings

    @classmethod
    def parseBios(cls, file):
        """
        Parse output from /opt//ibm/toolscenter/asu//asu64  showvalues

        Params
        -----
        file: array|file handle
        An open file handle or an array

        Returns
        -------
        Dictionary of key/value pairs, key is the setting, value is the selection
        """
        settings = {}

        for line in file:
            if re.search('^CMOS_', line):
                parts = line.rstrip('\n').split('=')
                setting=parts[0]
                value=parts[1]
                settings[setting] = value

        return settings

    @classmethod
    def openFile(cls, filename):
        """
        Open a file. 
        
        Params
        ------
        filename : string
        The name of the file. If '-' is the filename, then stdin will be opened
        """
        if filename == "-":
            file = sys.stdin
        else:
            file = open(filename, 'r')
        return file

    @classmethod
    def failsTest(cls, couch):
        """
        """
        return couch.getView('blade', 'fails_test')

    @classmethod
    def serialNumberToDocId(cls, couch):
        """
        Return a dictionary of serial number to doc Ids
        Returns
        -------
        The docId of the blade with the specified serial number
        """
        return couch.getView('blade', 'serial_number_to_doc_id')

    @classmethod
    def isValidMac(cls, mac):
        """
        Returns
        -------
        None if this is an invalid mac address, 1 otherwise
        """
        return re.search(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac, re.I)

class Slot (CouchDoc):
    """
    Defines a slot in a BladeCenter H Chassis. In the Nanek
    cluster, a slot defines the node number, or the node name.
    Any Blade can go into any Slot, but the node's name
    is defined by the Chassis.num * 14 + slot.num - 1

    Attributes
    ----------
    docId
    persistentAttributes

    nodeName     : string
                   The name of the node in this slot
    num          : int
                   The number of the slot
    chassisDocId : string
                   The docId of the Chassis to which this slot belongs
    bladeDocId   : string, optional
                   The docId of the Blade that is in this slot
    """
    @property
    def type(self):
        """
        Returns:
        -------
        A text representation of the type of object. Stored
        as the type attribute in Couch
        """
        return 'slot'

    @property
    def docId(self):
        """
        Returns
        -------
        string
            The unique document ID for this object used by CouchDB
        """
        return '%s:slot-%02d' % (self.chassisDocId, self.num)

    @property
    def persistentAttributes(self):
        """
        Returns
        -------
            An array attributes that will be persisted to CouchDB
        """
        return ['nodeName', 'num', 'chassisDocId', 'bladeDocId', 'bladeInstalled', 'bladeCommunicating']
        
    @classmethod
    def retrieveWithMac(cls, couch, mac):
        """
        Find a slot that matches the specified mac address

        Params
        ------
        couch:  object
                couch database connection
        mac:    string
                The mac address for which to search

        Returns
        -------
        Dictionary of key/value pairs for the slot that matches the specified mac address
        """
        if mac == 'not available' or mac == 'not installed':
            return None

        output = couch.getView('slot', 'mac_to_slot', mac)
        Log.debug(200, output)
        if output and len(output) > 0:
            key, value = output.popitem()
            if value:
                return value

        return None

    @classmethod
    def communicationProblems(cls, couch):
        """
        Find all slots with communication problems
        
        Params:
        -------
        couch:  object
                couch database connection
        
        Returns:
        --------
        A dictionary mapping slot docIds to slots parameters of slots with
        communication problems
        """
        return couch.getView('slot', 'communication_problems')

    @classmethod
    def toBlade(cls, couch, slotDocId):
        """
        Find the slotDocId / bladeDocId tuple for the specified blade
        
        Params:
        -------
        Params:
        -------
        couch:  object
                couch database connection
        
        slotDocId: string
                   The slot document ID
        
        Returns:
        --------
        If the slotDocId is found, and it has a bladeDocId, a (slotDocId, bladeDocId)
        tuple is returned. Otherwise, None is returned
        """
        return couch.getViewTuple('slot', 'slot_to_blade', slotDocId)

class LogEntry (CouchDoc):
    def __init__(self, params):
        """
        Constructor

        Parameters
        ----------
        params : dictionary
             Set of attributes
        """
        super(LogEntry, self).__init__(params)
        self.docId = '%s' % uuid.uuid4()

    @property
    def type(self):
        """
        Returns:
        -------
        A text representation of the type of object. Stored
        as the type attribute in Couch
        """
        return 'log_entry'

    @property
    def persistentAttributes(self):
        """
        Returns
        -------
            An array attributes that will be persisted to CouchDB
        """
        return ['slotDocId', 'bladeDocId', 'chassisDocId', 'timestamp', 'severity', 'serviceableFlag', 'eventID', 'rawAttribute', 'message', 'source', 'memoryReplaced']
        
    @classmethod
    def all(cls, couch, dateRange = None):
        """
        Find all LogEntry objects

        Params
        ------
        couch:   object
                 A CouchDB object

        Returns
        -------
        A dictionary of LogEntry docIds mapped to the document
        """
        params = {'includeDocs': 1}

        if dateRange:
            params.update(dateRange)

        return couch.getViewTuple('log_entry', 'all', params)

    @classmethod
    def allNotInfo(cls, couch, params = None):
        """
        Find all LogEntry objects that do not have a severity
        of INFO

        Params
        ------
        couch:   object
                 A CouchDB object

        Returns
        -------
        A dictionary of LogEntry docIds mapped to the document
        """
        if params is None:
            params = {}

        params['includeDocs'] = 1
        return couch.getViewTuple('log_entry', 'all_not_info', params)

    @classmethod
    def bladeErrors(cls, couch, bladeDocId = None):
        """
        Get the entire set of blade error log entries. Repeated events are
        discarded and only the first event is reported

        Params
        ------
        couch:   object
                 A CouchDB object

        bladeDocId: string
                    Restricts results to a single blade. If not specified, all
                    results will be returned. This is too much data, so don't do that

        Returns
        -------
        A dictionary of bladeDocId keys to an array of LogEntry dictionaries
        """
        params = {'includeDocs': 1}

        if bladeDocId:
            params['key'] = bladeDocId

        results = couch.getViewDict('log_entry', 'blade_errors', params)

        if not results:
            return None

        # The log entries to return
        logEntries = {}
        
        if results:
            for result in results:
                key = result
                values = results[key]

                filteredValues = []

                # If the current value is an array, set, etc, append this value
                if isinstance(values, (frozenset, list, set, tuple)):
                    prevEventID = ''
                    for value in values:
                        eventID = value.get('eventID', None)
                        if eventID:
                            if eventID != prevEventID:
                                filteredValues.append(value)
                                prevEventID = value['eventID']
                        else:
                            filteredValues.append(value)


                else:
                    filteredValues = [values]

                logEntries[key] = filteredValues

        return logEntries

class Chassis (CouchDoc):
    """
    Defines a Nanek or NMC mini-cluster BladeCenter H Chassis.

    Attributes
    ----------
    docId
    persistentAttributes
    nodeNameFormat    : string
                        The format for node names, ex: ns%03d
    chassisNameFormat : string
                        The format for the chassis name, ex: ns-mm%03d
    host              : string
                        The IP address or host name of the chassis
    num               : int
                        The chassis number
    firstNode         : int
                        The first node number in the chassis, eg 1 or 15 
    lastNode          : int
                        The last node number in the chassis, eg 14 or 28
    community         : string
                        The SNMP community string
    """
    def __init__(self, params):
        """
        Constructor

        Parameters
        ----------
        params : dictionary
             Set of attributes
        """
        super(Chassis, self).__init__(params)

        self.isPingable = 0
        self.collectedSNMP = 0

        if params:
            setattr(self, 'nodeNameFormat', params['nodeNameFormat'])
            setattr(self, 'chassisNameFormat', params['chassisNameFormat'])

    @property
    def type(self):
        """
        Returns:
        -------
        A text representation of the type of object. Stored
        as the type attribute in Couch
        """
        return 'chassis'

    @property
    def docId(self):
        """
        Returns
        -------
        string
            The unique document ID for this object used by CouchDB
        """
        return 'chassis-%03d' % self.num

    def ping(self):
        """
        Returns
        -------
        None if the chassis was not pingable
        """
        (output, exitcode) = Command.run(["/bin/ping", "-c1", "-w100", self.host])
        if exitcode == 0:
	    return True
        return None

    def powerState(self):
        """
        Get the power state for all slots
        """
        walkAttr = 'remoteControlBladePowerState'
        oid = 'BLADE-MIB::%s' % walkAttr

        # Start async snmpwalk. This call returns immediately
        # and spawns a background thread to perform the SNMPWalk
        snmpWalk = SNMPWalk.withConfigFile(self.host, oid)

        state = []

        # While the snmpwalk is running
        while not snmpWalk.eof:
            # Get snmp oid/value pairs off the queue
            while not snmpWalk.queue.empty():
                (oid, value) = snmpWalk.queue.get()
                (mibName, attr, lastOctet) = snmpWalk.extractOidParts(oid)

                if attr == walkAttr:
                    if value == 'on(1)':
                        state.append(1)
                    else:
                        state.append(0)
        snmpWalk.join()
        Log.debug(100, 'ch %03d power state: %s' % (self.num, state))
        return state

    def powerCycleSlot(self, slot):
        snmp = SNMP.withConfigFile(self.host)
        snmp.set('BLADE-MIB::restartBlade.%d' % slot, 'i', '1')

    def powerCycle(self):
        """
        Power cycle all slots
        """
        if self.ping():
            for slot in range(1, 15):
                self.powerCycleSlot(slot)
        else:
            Log.info('%s not pingable, cannot power cycle all blades' % self.host)

    def powerOnOffSlot(self, slot, func):
        """
        Power on a single slot
        
        Params
        ------
        slot : int
               The slot number
        func:  int
               0 = off, 1 = on, 2 = soft off
        """
        snmp = SNMP.withConfigFile(self.host)
        snmp.set('BLADE-MIB::powerOnOffBlade.%d' % slot, 'i', str(func))
        
    def powerOnOff(self, func):
        """
        Power on / off all slots in the chassis

        func:  int
               0 = off, 1 = on, 2 = soft off
        """
        if self.ping():
            for slot in range(1, 15):
                self.powerOnOffSlot(slot, func)
        else:
            Log.info('%s is not pingable, cannot apply power func %d all slots' % (self.host, func))

    def collectInfoAndPersist(self, couch):
        """
        Collect blade info for this chassis via SNMP, and 
        persist those blades and slots and this Chassis object
        to CouchDB when done
        """
        if not self.ping():
            Log.info('%s not pingable, not collecting SNMP info' % self.host)
        else:
            Log.debug(5, '%s is pingable' % self.host)
            self.isPingable = 1

            snmp = SNMP.withConfigFile(self.host)

            self.collectChassisInfo(snmp)
            self.collectFanPackInfo()

            bladesCommunicating = bitarray(self.bladesCommunicating)
            bladesInstalled = bitarray(self.bladesInstalled)

            oids = {'mac0':                     'BLADE-MIB::bladeMACAddress1Vpd',
                    'mac1':                     'BLADE-MIB::bladeMACAddress2Vpd',
                    'biosVersion':              'BLADE-MIB::bladeBiosVpdRevision',
                    'bmcVersion':               'BLADE-MIB::bladeSysMgmtProcVpdRevision',
                    'diagVersion':              'BLADE-MIB::bladeDiagsVpdRevision',
                    'serialNumber':             'BLADE-MIB::bladeBiosVpdName',
                    'healthState':              'BLADE-MIB::bladeHealthState',
                    'healthSummarySeverity':    'BLADE-MIB::bladeHealthSummarySeverity',
                    'healthSummaryDescription': 'BLADE-MIB::bladeHealthSummaryDescription',
                }

            blade = {}
            
            for (attr, oid) in oids.items():
                values = self.bladeInfo(snmp, oid)
                if values:
                    for (slot, value) in values:
                        if not blade.has_key(slot):
                            blade[slot] = {}
                        blade[slot][attr] = value

            if len(blade) > 0:
                self.collectedSNMP = 1
                for (slotNum, params) in blade.items():
                    Log.debug(10, 'chassis %d slot %s blade params: %s' % (self.num, slotNum, params))
                    nodeNum = (int(slotNum) - 1) + self.firstNode
                    nodeName = self.nodeNameFormat % nodeNum

                    blade = Blade(params)

                    slotInt = int(slotNum)

                    slotParams = {'num':                slotInt,
                                  'nodeName':           nodeName,
                                  'chassisDocId':       self.docId,
                                  'bladeDocId':         blade.mac0,
                                  'bladeInstalled':     bladesInstalled[slotInt - 1],
                                  'bladeCommunicating': bladesCommunicating[slotInt - 1],
                              }

                    slot = Slot(slotParams)

# This appears to be pointless. We shouldn't save any information about blades that
# are not available
#                    if blade.mac0 == 'not available':
#                        blade.mac0 = '%s-%s' % (blade.mac0, slot.docId)

                    slot.persist(couch)

                    if blade.validMac0:
                        blade.persist(couch)

        self.persist(couch)

    def bladeInfo(self, snmp, inOid):
        """
        Retrieve information about blades in a chassis
        """
        values = snmp.walk(inOid)
        slotValues = []
        for (oid, value) in values:
            slot = snmp.extractLastOctet(oid)
            if slot:
                slotValues.append( (slot, value) )
                
                if not slotValues:
                    Log.error('No results for %s %s' % (host, inOid))

        return slotValues

    def collectChassisInfo(self, snmp):
        """
        Retrieve chassis information
        """ 
        for (attr, oid) in self.chassisOidDict.items():
            values = snmp.walk(oid)
            if values:
                Log.debug(10, '%s: %s' % (attr, values[0][1]))
                setattr(self, attr, values[0][1])

    def collectFanPackInfo(self):
        oid = 'BLADE-MIB::fanPack'

        # Start async snmpwalk. This call returns immediately
        # and spawns a background thread to perform the SNMPWalk
        snmpWalk = SNMPWalk.withConfigFile(self.host, oid)

        # While the snmpwalk is running
        while not snmpWalk.eof:
            # Get snmp oid/value pairs off the queue
            while not snmpWalk.queue.empty():
                (oid, value) = snmpWalk.queue.get()
                (mibName, attr, lastOctet) = snmpWalk.extractOidParts(oid)

                if attr != 'fanPackIndex': 

                    if hasattr(self, attr):
                        attrValue = getattr(self, attr)
                        attrValue.append(value)
                        setattr(self, attr, attrValue)
                    else:
                        setattr(self, attr, [value])


        snmpWalk.join()

    def parseEventLogAttribute(self, line, serialNumberToDocId):
        """
        Parse a line of format
           'Severity:INFO  Source:Blade_11  Serviceable Flag: U  EventID:0x10000002  Name:SN#YK13A082B0KY  Date:07/15/15  Time:22:04:08
        Into its key value pairs
        """
        # keep the raw line, just in case parsing fails
        dict = {'rawAttribute': line, 'chassisDocId': self.docId}

        # Some assumptions:
        #
        # The keys will always be in this order and named this way
        # Values will never have spaces
        #
        # A firmware update could change this, or maybe some unknown corner case exists. This
        # is why the rawAttribute is stored.
        #
#        match = re.search('^Severity:(\S+)\s+Source:(\S+)\s+Serviceable Flag:(\S+)\s+EventID:(\S+)\s+Name:(\S+)\s+Date:([0-9]+)\/([0-9]+)/([0-9]+)\s+Time:([0-9]+):([0-9]+):([0-9]+)$', line)

        # Corner case, Name is blank
        # Severity:INFO Source:Audit Serviceable Flag: U EventID:0x0001608c Name: Date:02/19/15 Time:14:08:20
        match = re.search('^Severity:(\S+)\s+Source:(\S+)\s+Serviceable Flag:\s+(\S+)\s+EventID:(\S+)\s+Name:(\S*)\s+Date:([0-9]+)\/([0-9]+)/([0-9]+)\s+Time:([0-9]+):([0-9]+):([0-9]+)$', line)

        if match:
            datetimeKeys = ['month', 'day', 'year', 'hour', 'minute', 'second']
            keys = ['severity', 'source', 'serviceableFlag', 'eventID', 'name']
            keys.extend(datetimeKeys)
            idx = 1
            for key in keys:
                dict[key] = match.group(idx)
                idx = idx + 1

            month  = int(dict.get('month',  1))
            day    = int(dict.get('day',    1))
            year   = int(dict.get('year',   1970))
            hour   = int(dict.get('hour',   0))
            minute = int(dict.get('minute', 0))
            second = int(dict.get('second', 0))

            # Years come from the AMM offset from 2000
            if year < 1970:
                year = year + 2000

            dt = datetime.datetime(year, month, day, hour, minute, second, 0)

            dict['timestamp'] = dt.isoformat()

            # Remove date/time keys
            for key in datetimeKeys:
                del dict[key]

            # If this is a blade, extract the blade number and turn it into a slotDocId
            match = re.search('Blade_([0-9]+)', dict['source'])
            if match:
                dict['slotDocId'] = '%s:slot-%02d' % (self.docId, int(match.group(1)))

            # Match the serial number to a bladeDocId, if possible
            if serialNumberToDocId.has_key(dict['name']):
                dict['bladeDocId'] = serialNumberToDocId[dict['name']]

        return dict

    def collectAndClearEventLog(self, couch):
        log = {}

        # OIDs to retrieve
        oids = ['BLADE-MIB::readEnhancedEventLogAttribute', 'BLADE-MIB::readEnhancedEventLogMessage']

        # Get the mapping of blade serial numbers to blade document ids
        serialNumberToDocId = Blade.serialNumberToDocId(couch)

        for oid in oids:

            # Start async snmpwalk. This call returns immediately
            # and spawns a background thread to perform the SNMPWalk
            snmpWalk = SNMPWalk.withConfigFile(self.host, oid)

            # While the snmpwalk is running
            while not snmpWalk.eof:
                # Get snmp oid/value pairs off the queue
                while not snmpWalk.queue.empty():
                    (oid, value) = snmpWalk.queue.get()
                    (mibName, oidBase, lastOctet) = snmpWalk.extractOidParts(oid)

                    if oidBase != 'readEnhancedEventLogNumber':
                        # Start with an empty dictionary
                        dict = {}

                        # Get the existing log entry, if it exists
                        if log.has_key(lastOctet):
                            dict = log[lastOctet]

                        # Update the dictionary with this line from the snmpwalk
                        if oidBase == 'readEnhancedEventLogAttribute':
                            dict.update(self.parseEventLogAttribute(value, serialNumberToDocId))
                        else:
                            match = re.search('^Text:(.*)$', value)
                            if match:
                                value = match.group(1)

                            dict.update({'message': value})

                        # Update the log entry list
                        log[lastOctet] = dict

                        # On the final snmp walk command, create CouchDB objects
                        if dict and oidBase == 'readEnhancedEventLogMessage':
                            logEntry = LogEntry(dict)
                            logEntry.persist(couch)

            # Join snmpwalk background thread
            snmpWalk.join()
        
        snmp = SNMP.withConfigFile(self.host)
        snmp.set('BLADE-MIB::clearEventLog.0', 'i', '1')

        Log.info('%s system log entries collected from %s' % (len(log), self.name))
        
    @property
    def name(self):
        """
        Returns
        -------
        string
            The name of this chassis
        """
        return self.chassisNameFormat % self.num

    @property
    def persistentAttributes(self):
        """
        Returns
        -------
            An array attributes that will be persisted to CouchDB
        """
        oidAttr = self.chassisOidDict.keys()
        attr = ['num', 'name', 'host', 'firstNode', 'lastNode', 'isPingable', 'collectedSNMP', 'fanPackState', 'fanPackAverageSpeed', 'fanPackControllerState', 'fanPackCount', 'fanPackAverageSpeedRPM']

        attr.extend(oidAttr)
        return attr

    @property
    def chassisOidDict(self):
        """"
        Returns
        -------
        A dictionary of chassis document keys that maps to SNMP OIDs
        """
        return {'ammFirmware':                'BLADE-MIB::mmMainApplVpdBuildId.1',
                'bladesInstalled':            'BLADE-MIB::bistBladesInstalled.0',
                'bladesCommunicating':        'BLADE-MIB::bistBladesCommunicating.0',
                'powerModulesInstalled':      'BLADE-MIB::bistPowerModulesInstalled.0',
                'powerModulesFunctional':     'BLADE-MIB::bistPowerModulesFunctional.0',
                'switchModulesInstalled':     'BLADE-MIB::bistSwitchModulesInstalled.0',
                'switchModulesCommunicating': 'BLADE-MIB::bistSwitchModulesCommunicating.0',
                'healthSummarySeverity':      'BLADE-MIB::systemHealthSummarySeverity.1',
                'healthSummaryDescription':   'BLADE-MIB::systemHealthSummaryDescription.1',
                'healthSummaryDateTime':      'BLADE-MIB::systemHealthSummaryDateTime.1',
                'systemErrorLED':             'BLADE-MIB::systemErrorLED.0',
                'informationLED':             'BLADE-MIB::informationLED.0',
        }

    @classmethod
    def allBladesFailToNetboot(cls, couch):
        """
        Find a list of chassis where all blades failed to netboot
        
        Params
        ------
        couch:   object
                 A CouchDB object

        Returns
        -------
        A list of chassis docId
        """

        results = couch.getView('blade', 'failed_netboot')

        chassis = {}
        failedChassis = []

        for bladeDocId in results:
            slotInfo = Slot.retrieveWithMac(couch, bladeDocId)

            chassisDocId = None
            slotNum = None

            if slotInfo:
                Log.debug(200, 'slotInfo: %s' % slotInfo)
                if slotInfo.has_key(u'chassisDocId'):
                    chassisDocId = slotInfo[u'chassisDocId']

                if slotInfo.has_key(u'num'):
                    slotNum = slotInfo[u'num']

            if chassisDocId and slotInfo:
                if chassis.has_key(chassisDocId):
                    chassis[chassisDocId].append(slotNum)
                else:
                    chassis[chassisDocId] = [slotNum]

        for chassisDocId in sorted(chassis.iterkeys()):
            slots = chassis[chassisDocId]
            if len(slots) >= 14:
                failedChassis.append(chassisDocId)

        return failedChassis

    @classmethod
    def unreachableAMMs(cls, couch):
        """
        Find chassis with AMMs that are not reachable

        Params
        ------
        couch:   object
                 A CouchDB object

        Returns
        -------
        A list of chassis docId
        """
        return couch.getView('chassis', 'connectivity_problems')

    @classmethod
    def wrongFirmware(cls, couch):
        """
        Find chassis with the wrong firmware

        Params
        ------
        couch:   object
                 A CouchDB object

        Returns
        -------
        A list of chassis docId
        """
        return couch.getView('chassis', 'wrong_firmware')

    @classmethod
    def all(cls, couch):
        """
        Find all chassis

        Params
        ------
        couch:   object
                 A CouchDB object

        Returns
        -------
        A dictionary of chassis docIds mapped to empty strings
        """
        return couch.getViewTuple('chassis', 'all')

    @classmethod
    def failsTest(cls, couch):
        """
        Find all chassis that fails to test

        Params
        ------
        couch:   object
                 A CouchDB object

        Returns
        -------
        A list of tuples (chassis docId, dict of problems)
        """
        return couch.getViewTuple('chassis', 'fails_test')