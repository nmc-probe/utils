#!/usr/bin/python
#
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
#
# Collect SNMP information from IBM BladeCenter H Advanced
# Management Modules and put the data into a CouchDB 

import nmc,os,getopt,sys

from nmc.log import Log
from nmc.couchdb import CouchDB
from nmc.nanek import LogEntry

def main():
    """
    Program entry point
    """
    readOptions()

    # Couch database connector
    couch = CouchDB.withConfigFile()

    logEntries = LogEntry.all(couch)

    for entry in logEntries:
        Log.debug(1, 'Deleting %s' % entry)
        couch.delete(logEntries[entry])

def usage(progName):
    print ('%s: Delete all documents in CouchDB with type == log_entry. All documents')
    
def readOptions():
    progName = sys.argv[0]

    optlist = None
    args = None

    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'h', ['help'])

    except getopt.GetoptError as err:
        print(err)
        usage(progName)
    
    num=None

    # Process the options
    for (opt,value) in optlist:
        if opt == '--help' or opt == '-h':
            usage(progName)
            sys.exit(0)

# Program entry point
if __name__ == "__main__":
    main()
