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
# Collect information about a node and place that information into
# a CouchDB database

import nmc,os,sys,re

from nmc.couchdb import CouchDB
from nmc.log import Log
from nmc.nanek import Blade
from nmc.command import Command

couchHost = '10.55.0.5'
couchPort = 5984
couchDB = 'nanek'

expectedBiosSettings = '/root/expected_bios_settings'
asuCmd = ['/opt/ibm/toolscenter/asu/asu64', 'showvalues']

def main():
    """                                                                         
    Program entry point                                                         
    """
    # Couch database connector                                                  
    couch = CouchDB(couchHost, couchPort, couchDB)

    params = {
        'numCPUs':    Blade.discoverNumCPUs(),
        'memory':     Blade.discoverMemory(),
        'mac0':       Blade.discoverMac0(),
        'netbooted': 'true'
    }

    incorrectBIOS = Blade.discoverIncorrectBIOSSettings(expectedBiosSettings, asuCmd)
    if incorrectBIOS:
        if len(incorrectBIOS) > 0:
            params['incorrectBIOSSettings'] = incorrectBIOS
    else:
	params['incorrectBIOSSettings'] = 'None'

   
    blade = Blade(params)
    blade.persist(couch)

# Program entry point                                                           
if __name__ == "__main__":
    main()
