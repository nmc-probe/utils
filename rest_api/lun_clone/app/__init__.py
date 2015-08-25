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

from flask import Flask
from flask.ext.restful import Api, Resource, reqparse

from nmc_probe_rest.lun_clone import LUNClone, LUNCloneTest
#from nmc_probe_rest.zfs import SnapshotList, VolumeList, FilesystemList, AttributeList, Filesystem, Volume, Snapshot, Clone

app = Flask(__name__)
api = Api(app)

api.add_resource(LUNClone,     '/lun/api/v1.0/clone',      endpoint='clone')
api.add_resource(LUNCloneTest, '/lun/api/v1.0/clone_test', endpoint='clone_test')

manage_zfs = None

if manage_zfs is not None:
    api.add_resource(SnapshotList,   '/zfs/api/v1.0/snapshots',   endpoint='snapshots')
    api.add_resource(VolumeList,     '/zfs/api/v1.0/volumes',     endpoint='volumes')
    api.add_resource(FilesystemList, '/zfs/api/v1.0/filesystems', endpoint='filesystems')
    api.add_resource(AttributeList,  '/zfs/api/v1.0/attributes',  endpoint='attributes')

    api.add_resource(Filesystem, '/zfs/api/v1.0/filesystem',  endpoint='filesystem')
    api.add_resource(Volume,     '/zfs/api/v1.0/volume',      endpoint='volume')
    api.add_resource(Snapshot,   '/zfs/api/v1.0/snapshot',    endpoint='snapshot')
    api.add_resource(Clone,      '/zfs/api/v1.0/clone',       endpoint='clone')

if __name__ == '__main__':
    app.run(debug=True)
