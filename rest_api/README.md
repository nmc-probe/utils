# REST API for Creating and Preparing Clones 

Provides a RESTful API using python and flask to creating
and sharing iSCSI LUNs from ZFS clones and preparing them 
for use.

There are two major functions provided:

* Clone
* Prep

The clone functionality creates ZFS clones from snapshots and shares those cloned volumes over iSCSI. The prep function prepares those targets for use by doing things like setting the initiator name, hostname, and console parameters.

# API

The API was designed for a ZFS + iSCSI backend.

## Endpoint: `/lun/api/v1.0/clone`

### Method: POST

Creates an iSCSI target by creating a clone of a ZFS snapshot, then shares it over iSCSI. It is assumed that the source snapshot is a snapshot of a volume. 
If the destination clone already exists, then that existing volume will be used for the iSCSI share

<table>
<tr> <th> Parameter    </th> <th> Required </th> <th> Description </th> </tr>
<tr> <td> src          </td> <td> yes      </td> <td> Source snapshot for the volume </td> </tr>
<tr> <td> dst          </td> <td> yes      </td> <td> Destination volume to create </td> </tr>
<tr> <td> wwn          </td> <td> yes      </td> <td> WWN for the iSCSI target </td> </tr>
<tr> <td> initiators   </td> <td> yes      </td> <td> Array of WWNs of initiators that are allowed to </td> </tr>
<tr> <td> createParent </td> <td> no       </td> <td> If set, any parent datasets for the destination will be created, if needed. </td> </tr>
<tr> <td> properties   </td> <td> no       </td> <td> ZFS properties for the destination clone. If not provided, then the properties will be taken from t </td> </tr>
</table>

Example

```bash
curl -s -k \
   --key /etc/emulab/ssl/client.key \
   --cert /etc/emulab/ssl/client.crt \
    -X POST 
    -H 'Content-Type: application/json' \
    -d '{"initiators":
           ["iqn.2014-11.nmc-probe.org:2da412368f",
            "iqn.2014-11.nmc-probe.org:bf537c5b3f8"],
         "src": "ns-host/projects/testbed/images/centos70-probe@0001",
         "dst": "ns-host/projects/myproject/myexperiment/nodes/ns0001/centos70-probe.0001",
         "createParent": 1,
         "wwn": "iqn.2014-11.nmc-probe.org:myproject.myexperiment.ns0001.centos70-probe.0001"
         }' 
    https://192.168.0.2/lun/api/v1.0/clone
```

### Method: DELETE

Removes an iSCSI share and optionally deletes the supporting volume.

<table>
<tr> <th> Parameter    </th> <th> Required </th> <th> Description </th> </tr>
<tr> <td> dst          </td> <td> yes      </td> <td> Destination volume to delete </td> </tr>
<tr> <td> wwn          </td> <td> yes      </td> <td> WWN for the target to unshare </td> </tr>
<tr> <td> deleteClones </td> <td> no       </td> <td> If set, the underlying clone will be deleted </td> </tr>
</table>


Example:

```bash
curl -s -k \
   --key /etc/emulab/ssl/client.key \
   --cert /etc/emulab/ssl/client.crt \
   -X DELETE \
   -H 'Content-Type: application/json' \
   -d '{"dst": "ns-host/projects/myproject/myexperiment/nodes/ns0001/centos70-probe.0001",
        "deleteClones": 1,
        "wwn": "iqn.2014-11.nmc-probe.org:myproject.myexperiment.ns0001.centos70-probe.0001"}' \ 
   https://192.168.0.2/lun/api/v1.0/clone
```

## Endpoint: `/lun/api/v1.0/clone_test`

### Method: POST

Used to check to see if the API stack is up and running. This endpoint does not take any parameters.

Example:

```bash
curl -s -k --key /etc/nginx/ssl/client.key --cert /etc/nginx/ssl/client.crt https://localhost/lun/api/v1.0/clone_test
```

## Endpoint `/lun/api/v1.0/prep`


### Method: POST

Prepares an iSCSI target.

<table>
<tr> <th> Parameter      </th> <th> Required </th> <th> Description </th> </tr>
<tr> <td> initiator_wwn  </td> <td> Yes      </td> <td> Client initiator World Wide Name. For Linux, this usually written to /etc/iscsi/initiator.name and is part of the grub configuration</td> </tr>
<tr> <td> initiator_fqdn </td> <td> Yes      </td> <td> Fully qualified domain name of the client </td> </tr>
<tr> <td> target_wwn     </td> <td> Yes      </td> <td> World Wide Name for the iSCSI target that is the root </td> </tr>
<tr> <td> target_lun     </td> <td> No       </td> <td> Target Logical Unit Number. Default is 0. </td> </tr>
<tr> <td> target_part    </td> <td> Yes      </td> <td> Target partition. Probably 1 </td> </tr>
<tr> <td> target_ip      </td> <td> Yes      </td> <td> IP address of the iSCSI target server </td> </tr>
<tr> <td> target_port    </td> <td> No       </td> <td> Port for the iSCSI target server. Default is 3260 </td></tr>
<tr> <td> ctrl_iface     </td> <td> Yes      </td> <td> Emulab control interface name </td> </tr>
<tr> <td> ctrl_mac       </td> <td> Yes      </td> <td> MAC address of the control interface </td> </tr>
<tr> <td> console_port   </td> <td> Yes      </td> <td> Console port. For ttyS0, use 0, for ttyS1, use 1, etc. </td> </tr>
<tr> <td> console_speed  </td> <td> Yes      </td> <td> Console speed, usually 115200 </td> </tr>
<tr> <td> console_params </td> <td> Yes      </td> <td> Console params, usuall n1 </td> </tr>
</table>

Example

```bash
curl -s -k \
   --key /etc/emulab/ssl/client.key \
   --cert /etc/emulab/ssl/client.crt \
  -X POST -H 'Content-Type: application/json' \
  -d '{ "initiator_wwn":  "iqn.2014-11.nmc-probe.org:f5df9513e783", \
        "initiator_fqdn": "ns0001.myproject.myexperiment.northslope.nx", \
        "target_wwn":     "iqn.2014-11.nmc-probe.org:myproject.myexperiment.ns0001.centos70-probe.0001", \
        "target_lun":     0, \
        "target_part":    "1", \
        "target_ip":      "192.168.0.2", \ 
        "target_port":    "3260",
        "console_params": "n1", \
        "console_port":   "1", \
        "console_speed":  "19200", \
        "ctrl_iface":     "eth0", \
        "ctrl_mac":       "00:1a:64:bd:34:7c", \
        }' \
  https://192.168.0.3/lun/api/v1.0/prep
```

## Endpoint: `/lun/api/v1.0/prep_test`

### Method: POST

Used to check to see if the prep API stack is up and running. This endpoint does not take any parameters.

Example:

```bash
curl -s -k --key /etc/nginx/ssl/client.key --cert /etc/nginx/ssl/client.crt https://localhost/lun/api/v1.0/prep_test
```