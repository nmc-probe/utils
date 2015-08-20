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
        self.iscsi_discovery(params)
        self.iscsi_login(params)
        self.udevd_settle_down()
        self.mount(params)
#        chroot_prep(params)
#        dismount(params)
#        iscsi_logout(params)

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
            subprocess.check_call([mount_cmd, device, chroot])
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
                subprocess.check_call([mount_cmd, '-o', 'bind', bind_mount, dest])

    #-------------------------------------------------------------------------------
    # Dismount an image
    #
    # @param image_params   Image parameter dictionary
    #-------------------------------------------------------------------------------
    def dismount_image(self, params):
        chroot = params['chroot']
    
        # Mount /sys, /proc and /dev in image chroot
        bind_mounts = ['/sys', '/proc', '/dev']

        for bind_mount in bind_mounts:
            dest = chroot + bind_mount
            log_info_node(params, 'dismounting %s' % dest)
            subprocess.check_call([umount_cmd, dest])

        log_info_node(params, 'dismounting %s' % chroot)
        subprocess.check_call([umount_cmd, chroot])

    #-------------------------------------------------------------------------------
    # chroot call to prep an image
    #
    # @param chroot        The path to the chroot directory
    # @param image_params  Image parameter dictionary
    #-------------------------------------------------------------------------------
    def chroot_prep(self, params):
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
        argument_list = [chroot_cmd, chroot_dir, chroot_prep_image_cmd]
        for option in option_list:
            fixed_option = option.replace('iscsi_', '').replace('_', '-')
            argument = '--%s=%s' % (fixed_option, params[option])
            argument_list.append(argument)

        # Chroot call to prep image
        log_info_node(params, 'calling %s in chroot %s' % (chroot_prep_image_cmd, chroot_dir))
        subprocess.check_call(argument_list)

    #-------------------------------------------------------------------------------
    # Login / logout of an iscsi target
    #
    # @param cmd           Either -l or -u, -l for login, -u for logout
    # @param image_params  The image parameter dictionary
    #-------------------------------------------------------------------------------
    def iscsi_cmd(self, cmd, params):
        ip_port = '%s:%s' % (params['ip'], params['port'])
   
        action = 'into'
        if cmd == '-u':
            action = 'out of'
        log_info_node(params, 'logging %s iSCSI target %s' % (action, params['wwn']))

        subprocess.check_call([iscsiadm_cmd, '-m', 'node', cmd, '-T', params['wwn'], '-p', ip_port])

    #-------------------------------------------------------------------------------
    # iscsi discovery
    #
    # @param iscsi_target_server  
    #-------------------------------------------------------------------------------
    def iscsi_discovery(self, params):
        args = [iscsiadm_cmd, '-m', 'discovery', '-t', 'st', '-p', params['ip']]
        Log.info('iscsi target discovery on %s: %s' % (params['ip'], ' '.join(args)))
        subprocess.check_call(args)

    #-------------------------------------------------------------------------------
    # Log into an iscsi target
    #
    # @param node_param_list   list of all node paramegers
    #-------------------------------------------------------------------------------
    def iscsi_login(self, params):
        self.iscsi_cmd('-l', params)

    #-------------------------------------------------------------------------------
    # Log out of all iscsi targets
    #
    # @param node_param_list   list of all node paramegers
    #-------------------------------------------------------------------------------
    def iscsi_logout(self, params):
        self.iscsi_cmd('-u', params)

    #-------------------------------------------------------------------------------
    # Wait for udevd to create /dev/disk/by-path devices
    #-------------------------------------------------------------------------------
    def udevd_settle_down(self):
        subprocess.check_call([udevadm_cmd, 'trigger', 'block'])
        subprocess.check_call([udevadm_cmd, 'settle'])
    
