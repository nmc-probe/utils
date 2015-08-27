#!/usr/bin/python
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

import json,httplib,datetime,urllib

def main():
    base_iqn       = 'iqn.2014-11.nmc-probe.org'
    pool           = 'ns-host'
    fs             = 'localhost'
    port           = '5000'
    image_pid      = 'testbed'
    image_name     = 'centos70-probe'
    image_snapshot = '0001'
    prep_initiator = 'iqn.2014-11.nmc-probe.org:bf537c5b3f8'
    dest_pid       = 'testbed'
    dest_eid       = 'jbtest'

    nodes = {
        'nodea': 'iqn.2014-11.nmc-probe.org:2da412368f',
        'nodeb': 'iqn.2014-11.nmc-probe.org:30fca6a764d5',
        'nodec': 'iqn.2014-11.nmc-probe.org:3b71f47df5e4',
    }

    for node_name, initiator in nodes.iteritems():
        wwn = '%s:%s.%s.%s.%s.%s' % (base_iqn, dest_pid, dest_eid, node_name, image_name, image_snapshot)
        initiators = (initiator, prep_initiator)
#        create(fs, port, pool, image_pid, image_name, image_snapshot, dest_pid, dest_eid, node_name, wwn, initiators)
        delete(fs, port, pool, image_name, image_snapshot, dest_pid, dest_eid, node_name, wwn)

def create(fs, port, pool, image_pid, image_name, image_snapshot, dest_pid, dest_eid, node_name, wwn, initiators):
    snapshot = '%s/projects/%s/images/%s@%s' % (pool, image_pid, image_name, image_snapshot)
    dest     = '%s/projects/%s/%s/nodes/%s/%s.%s' % (pool, dest_pid, dest_eid, node_name, image_name, image_snapshot)

    params = {
        "src":          snapshot,
        "dst":          dest,
        "wwn":          wwn,
        "initiators":   initiators,
        "createParent": True,
    }

    print 'creating %s' % params

    path = '/lun/api/v1.0/clone'

    connection = httplib.HTTPConnection(fs, port)
    connection.connect()
    connection.request('POST', path,
                       json.dumps(params),
                       {
                           'Content-Type': 'application/json'
                       })

    result = json.loads(connection.getresponse().read())

    status = result.get(u'status', None)

    if status and status != 'ok':
        print 'Error: %s' % status


def delete(fs, port, pool, image_name, image_snapshot, dest_pid, dest_eid, node_name, wwn):

    dest     = '%s/projects/%s/%s/nodes/%s/%s.%s' % (pool, dest_pid, dest_eid, node_name, image_name, image_snapshot)
    device   = '/dev/zvol/%s' % dest

    params = {
        "name":         dest,
        "wwn":          wwn,
        "deleteClones": True
    }

    print 'deleting %s' % params

    path = '/lun/api/v1.0/clone'

    connection = httplib.HTTPConnection(fs, port)
    connection.connect()
    connection.request('DELETE', path,
                       json.dumps(params),
                       {
                           'Content-Type': 'application/json'
                       })

    result = json.loads(connection.getresponse().read())

    status = result.get(u'status', None)

    if status and status != 'ok':
        print 'Error: %s' % status

# Program entry point
if __name__ == "__main__":
    main()
