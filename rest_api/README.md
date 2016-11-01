# REST API for Creating Clones and iSCSI Targets

Provides a RESTful API using python and flask to creating
and sharing iSCSI LUNs from ZFS clones and preparing them
for use.

There are three endpoints:

* clone
* clone_status
* clone_test

The `clone` endpoint starts the creation or deletion of a set of clones and
shares those clones via iSCSI. The `clone_status` function reports back the
status of the clone creation / deletion job. `clone_test` is no-op function
that is provided to sysadmins to check to see if the REST API is available.

# Endpoint: `/lun/api/v1.0/clone`

This endpoint starts a job to create and delete disk clones and share / unshare
those clones as iSCSI targets.

This endpoint returns immediately and before the clones are created or deleted.
To check the status of the job, use the clone_status endpoint.

## Method: POST

Begins the creation of a set of iSCSI targets. Returns the job id and a status.
If the destination clones already exist, then they will be re-used.

An array of iSCSI targets to be created can be passed in a single call.

Input:

<table>
<tr> <th> Parameter    </th> <th> Required </th> <th> Description </th> </tr>
<tr> <td> src          </td> <td> yes      </td> <td> Source snapshot for the volume </td> </tr>
<tr> <td> dst          </td> <td> yes      </td> <td> Destination volume to create </td> </tr>
<tr> <td> wwn          </td> <td> yes      </td> <td> WWN for the iSCSI target </td> </tr>
<tr> <td> initiators   </td> <td> yes      </td> <td> Array of WWNs of initiators that are allowed to </td> </tr>
<tr> <td> createParent </td> <td> no       </td> <td> If set, any parent datasets for the destination will be created, if needed. </td> </tr>
</table>

Return:

<table>
<tr> <th> Parameter    </th> <th> Description </th> </tr>
<tr> <td> status       </td> <td> "ok" or "error" </td> </tr>
<tr> <td> job_id       </td> <td> The uuid for this job. </td> </tr>
</table>

Example

```bash
curl -s -k \
  --key /etc/emulab/rest_client.key \
  --cert /etc/emulab/rest_client.crt \
  -X POST \
  -H 'Content-Type: application/json' \
  -d '{"clones":[
          {"initiators": ["iqn.2014-11.nmc-probe.org:666cf3f7545"],
           "src": "na-jbod-02-p01/projects/testbed/images/centos72-probe@1",
           "dst": "na-jbod-02-p01/projects/testbed/yat/nodes/nodea.centos72-probe.0001",
           "createParent": 1,
           "wwn":"iqn.2014-11.nmc-probe.org:testbed.yat.nodea.centos72-probe.0001"}]}' \
   https://10.55.0.11/lun/api/v1.0/clone

{"status": "ok", "job_id": "6457624d-da51-426b-a719-008f106f7ab2"}
```

## Method: DELETE

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
  --key /etc/emulab/rest_client.key \
  --cert /etc/emulab/rest_client.crt \
  -X DELETE \
  -H 'Content-Type: application/json' \
  -d '{"clones":[{
           "dst": "na-jbod-02-p01/projects/testbed/yat/nodes/nodea.centos72-probe.0001",
           "wwn": "iqn.2014-11.nmc-probe.org:testbed.yat.nodea.centos72-probe.0001",
           "deleteClone": 1
       }]}' \
   https://10.55.0.11/lun/api/v1.0/clone

{"status": "ok", "job_id": "b80f26d6-25cb-4638-95ea-dd9272b020cd"}
```

# Endpoint: `/lun/api/v1.0/clone_status/[job_id]`

Reports the status of a clone / target creation / deletion job.

## Method: GET

Example:

```
curl -s -k \
  --key /etc/emulab/rest_client.key \
  --cert /etc/emulab/rest_client.crt \
  -X GET \
   https://10.55.0.11/lun/api/v1.0/clone_status/6457624d-da51-426b-a719-008f106f7ab2

{"status": "complete",
 "udevd_time": 0.140548,
 "num_targets": 1,
 "job_type": "create",
 "num_clones": 1,
 "num_requested": 1,
 "num_completed": 1,
 "target_time": 0.518237,
 "clone_time": 2.399769,
 "lag_time": 0.216792,
 "percent_completed": 1.0,
 "job_time": 3.652129}
```

# Endpoint: `/lun/api/v1.0/clone_test`

## Method: POST

Used to check to see if the API stack is up and running. This endpoint does not take any parameters.

Example:

```bash
curl -s -k \
    --key  /etc/nginx/ssl/client.key \
    --cert /etc/nginx/ssl/client.crt \
    https://localhost/lun/api/v1.0/clone_test
```
Expected response:

```
{"status": "ok", "message": "test"}
```
