# Home Server Ansible Project

## Description

This role is designed to leverage [podman quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) functionality to easily install **single containers** on a system in rootless or rootful mode. Due to usage of podman quadlet, containers are fully managed via systemd. The goal is to keep it as simple as possible and lower effort to install container based applications on a linux system. It is indended to setup home servers or development environmenst, not to deploy containers on scaling infrastructure like kubernetes.

## Requirements

- Ansible 2.9+
- Python 3
- SSH access to managed hosts
- Podman version > 5 installed on the remote system
- For rootless containers linux user must exist and linger must be enabeled.


## Usage

### Role variables
| variable | Description | Required | Default |
| ----------- | ----------- | ----------- | ----------- |
| **podman_quadlet_container_file_name:** | The file name of the quadlet unit file with a file extension of ``.container`` or ``.container.j2`` . | mandatory | no default |
| **podman_quadlet_caller_role_path:** | The path where ansible should look for your configuration files / templates, e.g. also the quadlet unit file. Typically either your playbook directory, or in case you include this role to your own application role, the role path of your application role. | mandatory | no default |
| **podman_quadlet_rootless_user_name:** |  The linux user, which will be used to run the container in rootless mode. You need to make sure the user exists before executing this role. It will not be automatically created. You also need to make sure linger is enabled for this user to be able to start the container during boot automatically ```loginctl enable-linger <username>``` | optional | no default |
| **podman_quadlet_volumes:** | The list of volumes related to the container. | optional | no default |
| **podman_quadlet_firewall_ports:** | The list of firewall ports that need to be enabeled. Format need to follow ``<portnumber>/<protocol>``, like e.g. ``8080/tcp`` or ``51820/udp``.| optional | no default |
|  |  |  |  |

### Rootless container example

```yaml
---
- name: Sample playbook to deploy nginx as a rootless container
  hosts: all

  roles:
    - role: podman-quadlet
      podman_quadlet_container_file_name: nginxrootless.container
      podman_quadlet_caller_role_path: "{{ playbook_dir }}"
      podman_quadlet_rootless_user_name: nginx 
      podman_quadlet_volumes:
        - name: nginxrootless-volume
          paths:
            - path: /index.html
              state: file
              owner: 1001 # optional: Default is uid of the rootless user
              group: 1001 # optional: Default is gid of the rootless user
              mode: "0644" # optional: Default is "0644"
      podman_quadlet_firewall_ports:
        - 8080/tcp

```

As a minimum configuration, you need to have the quadlet unit file ``{{ playbook_dir }}/files/nginxrootless.container`` with the following content:
```
[Unit]
Description=Nginx container
After=network.target

[Container]
Image=docker.io/library/nginx:latest
ContainerName=nginxrootless
Volume=nginxrootless-volume:/usr/share/nginx/html
PublishPort=8080:80/tcp

[Install]
WantedBy=multi-user.target

```

### Rootful container example

```yaml
---
- name: Sample playbook to deploy nginx as a rootful container
  hosts: all

  roles:
    - role: podman-quadlet
      podman_quadlet_container_file_name: nginxrootful.container
      podman_quadlet_caller_role_path: "{{ playbook_dir }}"
      podman_quadlet_volumes:
        - name: nginxrootful-volume
          paths:
            - path: /index.html
              state: file
              owner: 0 # optional: Default is 0
              group: 0 # optional: Default is 0
              mode: "0644" # optional: Default is "0644"
      podman_quadlet_firewall_ports:
        - 80/tcp

```

As a minimum configuration, you need to have the quadlet unit file ``{{ playbook_dir }}/files/nginxrootful.container`` with the following content:
```
[Unit]
Description=Nginx container
After=network.target

[Container]
Image=docker.io/library/nginx:latest
ContainerName=nginxrootful
Volume=nginxrootful-volume:/usr/share/nginx/html
PublishPort=80:80/tcp

[Install]
WantedBy=multi-user.target

```

### Istallation

```bash
...
```

### Playbook ececution


```bash
...
```

### How to run tests

#### Install molecule

Install system prerequisites
```bash
sudo dnf install -y \
  python3 \
  python3-pip \
  python3-virtualenv \
  gcc \
  libffi-devel \
  python3-devel \
  openssl-devel
```

Create and activate a virtual environment
```bash
python3 -m venv ~/.venvs/molecule
```

```bash
source ~/.venvs/molecule/bin/activate
```

Install Molecule and plugins
```bash
pip install --upgrade pip
pip install molecule ansible ansible-lint
```

#### Run tests

```bash
molecule reset && rm -rf ~/.cache/molecule && molecule test
```