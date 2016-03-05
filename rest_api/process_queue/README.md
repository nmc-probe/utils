# REST API for processing the LUN create / delete queue

Provides a RESTful API for processing the LUN create / delete queue.

# Configure nginx

This step assumes that lun_clone has already been installed and nginx is already
installed and configured

```bash
cat << EOF > /etc/nginx/conf.d/process_queue.conf
server {
    server_name _;
    listen       127.0.0.1:7171 default_server;
    root         /usr/share/nginx/html;

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/var/run/process_queue.sock;
    }

    error_page 404 /404.html;
        location = /40x.html {
    }

    error_page 500 502 503 504 /50x.html;
        location = /50x.html {
    }
}
EOF

# Install process_queue

## CentOS 7

Clone the repository
```bash
mkdir -p /usr/src/nmc-probe
cd /usr/src/nmc-probe
git clone https://github.com/nmc-probe/utils.git
```

Create the virtualenv

```bash
yum install python-virtualenv
yum groupinstall "Development Tools"
mkdir /home/process_queue
cd /home/process_queue
virtualenv env
./env/bin/pip install Flask-RESTful-extend rtslib_fb uwsgi sqlalchemy sqlalchemy-utils
```

Populate virtualenv with required nmc-probe/utils/ files and directories

```bash
cd /home/process_queue
ln -s /usr/src/nmc-probe/utils/rest_api/process_queue/app .
ln -s /usr/src/nmc-probe/utils/rest_api/process_queue/wsgi.py .
ln -s /usr/src/nmc-probe/utils/rest_api/process_queue/config.ini .
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe env/lib/python2.7/site-packages/nmc_probe
ln -s /usr/src/nmc-probe/utils/site-packages/nmc_probe_rest env/lib/python2.7/site-packages/nmc_probe_rest
```

Install systemd unit for process_lun_clone_queue
```bash
cat << EOF > /etc/systemd/system/process_lun_clone_queue.service
[Unit]
Description=uWSGI instance to serve process_queue
After=network.target

[Service]
User=root
Group=root
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin"
Environment="SQLITE_DB=/var/lun_clone/queue.db"
ExecStart=/usr/src/nmc-probe/utils/bin/process_lun_clone_queue

[Install]
WantedBy=multi-user.target
EOF
```

Start and enable process_lun_clone_queue

```bash
systemctl start process_lun_clone_queue
systemctl enable process_lun_clone_queue
```
Verify that the process_queue is running
```bash
systemctl status process_lun_clone_queue -l
```

Restart and watch the log:
```bash
systemctl restart process_lun_clone_queue && journalctl -l -u process_lun_clone_queue -f
```

