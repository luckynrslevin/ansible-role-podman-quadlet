# Home Server Ansible Project

## Description

This role is designed to leverage [podman quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) functionality to easily install **single containers** on a system in rootless or rootful mode. Due to usage of podman quadlet, containers are fully managed via systemd. The goal is to keep it as simple as possible and lower effort to install container based applications on a linux system. It is intended to setup home servers or development environments, not to deploy containers on scaling infrastructure like kubernetes.


## Requirements

- Ansible 2.9+
- Ansible modules
  - ansible.posix.firewalld
- Python 3
- SSH access to managed hosts
- Podman version > 5 installed on the remote system
- For rootless containers linux user must exist and linger must be enabeled.


## Usage

### Role variables

Available variables are listed below, see `defaults/main.yml` and examples below for further details:

| Parameter |  Comments |
| --------- | ----------- |
| **podman_quadlet_app_name** <br> string / required | The application name. |
| **podman_quadlet_files_templates_src_path** <br> path / required | The root path of your `templates` and `files` folders. Typically this will be either your `{{ playbook_dir }}` or your `{{ role_path }}`. |
| **podman_quadlet_file_names** <br> list of strings / required | The list of quadlet files / templates, currently supporting $name`.container`, $name`.container.j2`, $name`.pod`, $name`.pod.j2`, $name`.volume` and $name`.volume.j2` files. |
| **podman_quadlet_volumes_files_to_stage** <br> list of volumes and files per volume | Top level structure:<br> `- name:` of the podman volume and a related list of <br> &nbsp; &nbsp; &nbsp;`files:` or directories to be deployed on the volume, with the following subparameters: <br> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; `- src:` file path and name <br> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; `mode:` Mode of file or dir. Default for files 0644, for directories 0755. <br> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; `dest:` destination of the file <br> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; `state:` 'file' or 'directory' Default is `file` <br> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; `owner:` UID Default is the UID of the current ansible user <br> &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; `group:` GID; Default is the main group of the current ansible user |
| **podman_quadlet_rootless_user_name** <br>string | Linux system user name used to execute a rootless container |
 **podman_quadlet_firewall_ports** <br> list of strings | List of firewall ports to be managed |
| | |

### Rootless container example

```yaml
---
- name: Sample playbook to deploy nginx as a rootless container
  hosts: all

  roles:
    - role: podman_quadlet
      podman_quadlet_app_name: nginxrootless
      podman_quadlet_rootless_user_name: nginx
      podman_quadlet_files_templates_src_path: "{{ playbook_dir }}"
      podman_quadlet_file_names:
        - nginxrootless.container.j2
        - nginxrootless.volume
      podman_quadlet_volumes_files_to_stage:
        - name: nginxrootless
          files:
            - src: index.html
            - src: template.html.j2
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
    - role: podman_quadlet
      podman_quadlet_app_name: nginxrootful
      podman_quadlet_files_templates_src_path: "{{ playbook_dir }}"
      podman_quadlet_file_names:
        - nginxrootful.container
        - nginxrootful.volume
      podman_quadlet_volumes_files_to_stage:
        - name: nginxrootful
          files:
            - src: index.html
            - src: /template/template.html.j2
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

## TODO:
- add table see https://github.com/buluma/ansible-role-bootstrap/blob/main/README.md
- change readme structure, see https://github.com/geerlingguy/ansible-role-nginx
- add github actions for molecule tests
- test from macos host to remote server
- Create initial release
- Create public playbooks for actual applications
  - wireguard
  - syncthing
  - shairport-sync
  - lyrion music server
