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

import re, subprocess
from nmc.log import Log

class Assert:
    @classmethod
    def typeIs(cls, arg, tp):
        if not type(arg) is tp:
            message = 'Type %s required, received %s: %s' % (tp.__name__,  type(arg).__name__, repr(arg))
            Log.error(message)
            raise TypeError(message)
            
    @classmethod
    def typeIsNamespace(cls, arg):
        return cls.typeIs(arg, dict)

class CommandError(Exception):
    """Exception raised for errors when running a command.

    Attributes:
        exitcode -- the exitcode
        output -- array of lines of output from the command
        command -- array of arguments for the command
    """
    def __init__(self, output, exitcode, command):
        self.exitcode = exitcode
        self.output = output
        self.command = command

    def __str__(self):
        return repr(self.output)

class ZFS:
    def __init__(self):
        self.zfs = '/sbin/zfs'

    def getCount(self):
        if getattr(self, '_count', None) is None:
            self._count = 0
        else:
            self._count = self._count + 1

        return self._count

    @property
    def all(self):
        if getattr(self, '_all', None) is None:
            self._all = self.list('all')
        return self._all

    @property
    def filesystems(self):
        if getattr(self, '_filesystems', None) is None:
            self._filesystems = self.list('filesystem')
        return self._filesystems

    @property
    def bookmarks(self):
        if getattr(self, '_bookmarks', None) is None:
            self._bookmarks = self.list('bookmark')
        return self._bookmarks

    @property
    def volumes(self):
        if getattr(self, '_volumes', None) is None:
            self._volumes = self.list('volume')
        return self._volumes

    @property
    def snapshots(self):
        if getattr(self, '_snapshots', None) is None:
            self._snapshots = self.list('snap')
        return self._snapshots

    @property
    def attributes(self):
        if getattr(self, '_attributes', None) is None:
            self._attributes = self.getAttributes()
        return self._attributes

    def getAttributes(self):
        attributes = {}
        output = self.run(['get', 'all'])
            
        for line in output:
            # Break into (name, used, avail, refer, mountpoint)
            components = line.split()
            if len(components) == 4:
                name = components[0]
                property = components[1]
                value = components[2]
                source = components[3]
                    
                if not attributes.has_key(name):
                    attributes[name] = {}

                attributes[name][property] =  {'value': value, 'source': source}

        return attributes

    def run(self, args):
        '''Run a zfs command'''
        cmd = args
        cmd.insert(0, self.zfs)
        output = ''
        try:
            Log.info(' '.join(cmd))
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT).split('\n')
            self.udevd_settle_down()
        except subprocess.CalledProcessError, e:
            raise ValueError(str(e.output))

        # Remove the first list of output
        output.pop(0)

        return output

    def set(self, name, property, value):
        self.run(['set', '%s=%s' % (property, value), dataset])

    def udevd_settle_down(self):
        '''Wait for udevd to create /dev/zvol devices'''
        udevadm_cmd = '/usr/sbin/udevadm'
        subprocess.check_call([udevadm_cmd, 'trigger', 'block'])
        subprocess.check_call([udevadm_cmd, 'settle'])

    def create(self, params):
        '''zfs create
        
        params -- { name: name,
                    properties:   {property: value, p2: v2, ...},
                    volume:       {size: size, sparse: true|false}
                    createParent: true or false} }
        '''
        # If no arguments provided, return immediately
        if params is None:
            raise ValueError('zfs create function received no parameters')

        command = ['create']

        name         = params.get('name', None)
        properties   = params.get('properties', None)
        volume       = params.get('volume', None)
        createParent = params.get('createParent', None)

        if not name:
            raise ValueError('zfs create function needs a name parameter')

        if createParent:
            command.append('-p')

        if not properties is None:
            for property, value in properties.iteritems():
                command.append('-o')
                command.append('%s=%s' % (property, value))

        if not volume is None:
            size = volume.get('size', None)
            sparse = volume.get('sparse', None)

            if not size:
                raise ValueError('Volumes must have a size attribute')

            command.append('-V')
            command.append(size)

            if sparse and sparse != False:
                command.append('-s')

        command.append(name)

        if self.all.has_key(name):
            if volume:
                Log.info('%s already exists. Not creating volume' % name)
            else:
                Log.info('%s already exists. Not creating filesystem' % name)
        else:
            self.run(command)

    def destroy(self, params):
        # Verify that parameters were received
        if params is None:
            raise ValueError('zfs destroy function received no parameters')

        # Get the name
        name = params.get('name', None)

        if not name:
            raise ValueError('zfs destroy function needs a name parameter')

        if self.all.has_key(name):
            command = ['destroy', name]
            self.run(command)
        else:
            Log.info('%s does not exist. Cannot destroy' % name)

    def snapshot(self, params):
        if params is None:
            raise ValueError('zfs snapshot function received no parameters')

        name = params.get('name', None)

        if name is None:
            raise ValueError('zfs snapshot function needs a name parameter')

        if not self.all.has_key(name):
            command = ['snapshot', name]
            self.run(command)
        else:
            Log.info('%s already exists. Not creating snapshot' % name)

    def clone(self, params):
        if params is None:
            raise ValueError('zfs clone function received no parameters')

        command = ['clone']

        snapshot     = params.get('snapshot', None)
        properties   = params.get('properties', None)
        dest         = params.get('dest', None)
        createParent = params.get('createParent', None)

        if not snapshot:
            raise ValueError('zfs clone function needs a snapshot parameter')

        if not dest:
            raise ValueError('zfs clone function needs a dest parameter')

        if createParent:
            command.append('-p')

        if not properties is None:
            for property, value in properties.iteritems():
                command.append('-o')
                command.append('%s=%s' % (property, value))

        command.append(snapshot)
        command.append(dest)

        if self.all.has_key(snapshot):
            if self.all.has_key(dest):
                Log.info('%s already exists. Not creating clone' % dest)
            else:
                self.run(command)
        else:
            raise ValueError('Snapshot %s does not exist, clone %s cannot be created' % (snapshot, dest))
        
    def list(self, opts = None):
        args = ['list']

        if opts:
            args.append('-t')
            args.append(opts)

        # Get list
        output = self.run(args)

        # Empty hash of datasets
        datasets = {}

        # Process each line of output
        for line in output:
            # Break into (name, used, avail, refer, mountpoint)
            components = line.split()
            if len(components) == 5:
                datasets[components[0]] = {
                    'available':  components[1],
                    'refer':      components[2],
                    'used':       components[3],
                    'mountpoint': components[4]
                }

        return datasets
