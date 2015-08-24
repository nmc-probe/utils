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

import sys, os, subprocess, time
from nmc_probe.log import Log

# Command locations
mount_cmd             = '/usr/bin/mount'
umount_cmd            = '/usr/bin/umount'
iscsiadm_cmd          = '/usr/sbin/iscsiadm'
chroot_prep_image_cmd = '/usr/local/sbin/prep_image.py'
chroot_cmd            = '/usr/sbin/chroot'
udevadm_cmd           = '/usr/sbin/udevadm'

# Base path for image mounts
image_mount_base = '/mnt/images'

def log_info_node(params, message):
    message = '%s: %s' % (params['name'], message)
    Log.info(message)

def log_error_node(params, message):
    message = '%s: %s' % (params['name'], message)
    Log.error(message)

class LUNPrep:
    def __init__(self, params):
        Log.info('params: %s' % params)

        required = ['ip', 'wwn', 'console_port', 'console_speed', 'console_params', 'ctrl_iface', 'ctrl_mac', 'fqdn', 'lun', 'part']
        missing = []

        for arg in required:
            value = params.get(arg, None)
            if value is None:
                missing.append(arg)

        Log.info(params)

        if len(missing) == 1:
            raise ValueError('Missing parameter: %s' % missing[0])
        elif len(missing) > 1:
            raise ValueError('Missing parameters: %s' % ', '.join(missing))

        params['name'] = params['fqdn'].split('.')[0]
        params['device'] = self.iscsi_device(params)
        params['chroot'] = self.chroot_dir(params)

        self.prep(params)

    def prep(self, params):
        # Add the target to the database
        self.iscsi_target_cmd(params, ['-o', 'new'])

        # Defensive maneuver:
        #
        # Just in case the target does not get deleted, this prevents automatic login
        # on reboot. Auto login can cause multiple connections to a block device to be
        # open which in the case of ZFS + iSCSI sharing, causes massive slowdowns
        # and possible corruption
        self.iscsi_target_cmd(params, ['-o', 'update', '-n', 'node.startup', '-v', 'manual'])
        self.iscsi_target_cmd(params, ['-o', 'update', '-n', 'node.conn[0].startup', '-v', 'manual'])

        # Log into the target
        self.iscsi_target_cmd(params, ['-l'])

        # Wait for udevd to settle down and for the device to be created
        self.udevd_settle_down()

        # Mount the target
        self.mount(params)

        # Prep the target
        self.chroot_prep(params)

        # Dismount
        self.dismount(params)

        # Logout and delete
        self.iscsi_target_cmd(params, ['-u'])
        self.iscsi_target_cmd(params, ['-o', 'delete'])

    def iscsi_device(self, params):
        return '/dev/disk/by-path/ip-%s:%s-iscsi-%s-lun-%s-part%s' % (params['ip'],
                                                                      params['port'],
                                                                      params['wwn'],
                                                                      params['lun'],
                                                                      params['part'])

    def chroot_dir(self, params):
        return image_mount_base + '/' + params['wwn']

    def mount(self, params):
        '''Mount an image
    
        Parameters
        ----------
        params : string
            Image parameter dictionary
        '''
        chroot = params['chroot']
        device = params['device']

        Log.info('device %s' % device)

        # Sanity check, destination shouldn't be a file
        if os.path.isfile(chroot):
            log_error_node(params, '%s is a file, can not mount %s at this location' % (chroot, device, params['vnode_name']))
            return

        # Make sure the destination exists
        if not os.path.exists(chroot):
            log_info_node(params, 'mkdir %s' % chroot)
            os.makedirs(chroot)

        # If the destination is already mounted, then
        # no need to mount again. It's likely the correctly mounted
        # device from a previous prep run that died
        if not os.path.ismount(chroot):
            log_info_node(params, 'mount %s %s' % (device, chroot))
            self.run([mount_cmd, device, chroot])
        else:
            log_info_node(params, '%s already mounted, hoping for the best' % chroot)

        # Mount /sys, /proc and /dev in image chroot
        bind_mounts = ['/sys', '/proc', '/dev']

        if not os.path.ismount(chroot):
            log_error_node(params, 'mount of %s failed, cannot mount %s in chroot' % (chroot, bind_mounts))
        else:
            for bind_mount in bind_mounts:
                dest = chroot + bind_mount
                log_info_node(params, 'mount -o bind %s %s' % (bind_mount, dest))
                self.run([mount_cmd, '-o', 'bind', bind_mount, dest])

    def dismount(self, params):
        '''Dismount an target lun
        
        Parameters
        params : dict
            Dictionary of parameters for the target lun
        '''
        chroot = params['chroot']
    
        # Mount /sys, /proc and /dev in image chroot
        bind_mounts = ['/sys', '/proc', '/dev']

        for bind_mount in bind_mounts:
            dest = chroot + bind_mount
            log_info_node(params, 'dismounting %s' % dest)
            self.run([umount_cmd, dest])

        log_info_node(params, 'dismounting %s' % chroot)
        self.run([umount_cmd, chroot])

    def chroot_prep(self, params):
        '''Call the prep command that is inside the LUN'''

        # Example command
        #
        # /chrootdir/usr/local/bin/lun_prep
        #    --initiator-name=iqn.2014-11.nmc-probe.org:2da412368f 
        #    --target-ip=10.57.0.5
        #    --target-port=3260
        #    --target-wwn=iqn.2014-11.nmc-probe.org:testbed.testbed-singlenode.ns0001
        #    --ctrl-iface=enp2s4
        #    --ctrl-mac=00:1a:64:bd:34:7c
        #    --console-port=1
        #    --console-speed=19200
        #    --console-params=n1

        cmd_params = {
            '--initiator-name': params['initiator_name'],
            '--target-ip':      params['ip'],
            '--target-port':    params['port'],
            '--target-wwn':     params['wwn'],
            '--ctrl-iface':     params['ctrl_iface'],
            '--ctrl-mac':       params['ctrl_mac'],
            '--console-port':   params['console_port'],
            '--console-speed':  params['console_speed'],
            '--console-params': params['console_params'],
        }

        # Process arguments
        argument_list = [chroot_cmd, params['chroot'], chroot_prep_image_cmd]

        for key,value in cmd_params.iteritems():
            argument_list.append('%s=%s' % (key, value))

        # Chroot call to prep image
        log_info_node(params, 'running prep command %s' % (' '.join(argument_list)))
        subprocess.check_call(argument_list)

    #-------------------------------------------------------------------------------
    # chroot call to prep an image
    #
    # @param chroot        The path to the chroot directory
    # @param image_params  Image parameter dictionary
    #-------------------------------------------------------------------------------
    def chroot_prep_delete_me(self, params):
        chroot = params['chroot']

        # List of options / image_parameters to pass from image_params
        # to the node/image specific iscsi_prep command.
        #
        # The iscsi_prep command conveniently takes arguments
        # that are matched to the names of keys in the image_params
        # dictionary. Just need to add a '--' to the front of each key
        # to make things work
        option_list = ['iscsi_initiator_name',
                       'iscsi_target_ip',
                       'iscsi_target_port',
                       'iscsi_target_wwn',
                       'ctrl_iface',
                       'ctrl_mac',
                       'console_speed',
                       'console_port',
                       'console_params']

        # Build the argument list
        argument_list = [chroot_cmd, chroot, chroot_prep_image_cmd]
        for option in option_list:
            fixed_option = option.replace('iscsi_', '').replace('_', '-')
            argument = '--%s=%s' % (fixed_option, params[option])
            argument_list.append(argument)

        # Chroot call to prep image
        log_info_node(params, 'calling %s in chroot %s' % (chroot_prep_image_cmd, chroot_dir))
        self.run(argument_list)

    def iscsi_target_cmd(self, params, args):
        '''iscsiadm command base for a specific target, portal and port'''
        ip_port = '%s:%s' % (params['ip'], params['port'])
        cmd = [iscsiadm_cmd, '-m', 'node', '-T', params['wwn'], '-p', ip_port]
        cmd.extend(args)
        self.run(cmd)
        
    def udevd_settle_down(self):
        '''Wait for udevd to create /dev/disk/by-path devices'''
        self.run([udevadm_cmd, 'trigger', 'block'])
        self.run([udevadm_cmd, 'settle'])

    def run(self, args):
        '''Run a command, capture stderr and report the exception, if an exception happens'''
        Log.info('%s' % ' '.join(args))

        pipes = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = pipes.communicate()

        if pipes.returncode != 0:
            # an error happened!
            err_msg = "%s. Code: %s" % (stderr.strip(), pipes.returncode)
            raise Exception(err_msg)
    
