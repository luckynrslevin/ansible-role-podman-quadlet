# Ansible role: podman quadlet

## Description

Deploy containerized applications as systemd services using [Podman Quadlet](https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html) — with full support for both **rootless** and **rootful** containers.

This role automates the entire lifecycle: deploying quadlet unit files, managing volumes, staging configuration files, patching existing configs, and configuring the firewall. Containers are fully managed by systemd, enabling automatic startup on boot and integration with standard Linux service management.

Designed for **home servers** and **development environments** where simplicity and reproducibility matter — not for scaling infrastructure like Kubernetes.

### Key features

- **Rootless and rootful** container deployment via Podman Quadlet
- **Quadlet unit files**: `.container`, `.volume`, `.pod`, and `.network` (plain files or Jinja2 templates)
- **Volume file staging**: deploy config files and directories into volumes with correct ownership
- **Rootless UID/GID mapping**: automatically maps container-perspective UIDs via `podman unshare chown` — no manual subuid offset calculations needed
- **Config patching**: patch specific values in existing config files (YAML, JSON, INI, XML, key-value) without replacing the entire file
- **Firewall management**: open ports and configure port forwarding for rootless containers that cannot bind to privileged ports
- **Security by default**: rootless containers run without root privileges, using Linux user namespaces for isolation
- **Automatic container updates**: containers can opt in to registry-based auto-updates via Podman's `AutoUpdate=registry` and the `podman-auto-update.timer` systemd timer
- **Quadlet validation**: validates unit files before deployment using `QUADLET_UNIT_DIRS` scoped to the current service

## Requirements

- Ansible 2.9+
- Ansible modules
  - ansible.posix.firewalld
  - community.general.ini_file (only if using INI config patching)
  - community.general.xml (only if using XML config patching)
- Python 3 on managed hosts
- SSH access to managed hosts
- Podman version >= 5 installed on the remote system
- For rootless containers: Linux user must exist and systemd linger must be enabled


## Usage

### Role variables

Available variables are listed below, see `defaults/main.yml` and examples below for further details:

| Parameter |  Comments |
| --------- | ----------- |
| **podman_quadlet_app_name** <br> string / required | The application name. |
| **podman_quadlet_files_templates_src_path** <br> path / required | The root path of your `templates` and `files` folders. Typically this will be either your `{{ playbook_dir }}` or your `{{ role_path }}`. |
| **podman_quadlet_file_names** <br> list of strings / required | The list of quadlet files / templates, currently supporting $name`.container`, $name`.container.j2`, $name`.pod`, $name`.pod.j2`, $name`.volume`, $name`.volume.j2`, $name`.network` and $name`.network.j2` files. |
| **podman_quadlet_volumes_files_to_stage** <br> list of volumes and files per volume | Top level structure:<br /> `- name:` of the podman volume and a related list of<br />     `files:` or directories to be deployed on the volume, with the following subparameters:<br />     `- src:` file path and name <br> &nbsp;       `mode:` Mode of file or dir. Default for files 0644, for directories 0755. <br>        `dest:` destination of the file <br>        `state:` 'file' or 'directory' Default is `file` <br>        `owner:` UID inside the container (default: 0). See [Rootless UID/GID mapping](#rootless-uidgid-mapping). <br>        `group:` GID inside the container (default: 0). See [Rootless UID/GID mapping](#rootless-uidgid-mapping). |
| **podman_quadlet_rootless_user_name** <br>string | Linux system user name used to execute a rootless container. Role expects the Linux user to already exist on the system. Add necessary task to create and enable linger in your playbook before calling the role. |
| **podman_quadlet_volumes_config_patches** <br> list of volumes and patches per volume | Patches specific values in existing config files inside volumes (e.g., files created by the container on first start) instead of replacing entire files. See [Config patching](#config-patching). |
| **podman_quadlet_firewall_ports** <br> list of strings | List of firewall ports to open. E.g. `8080/tcp`, `9090/udp`, `32768-60999/tcp`. |
| **podman_quadlet_firewall_port_forwards** <br> list of port forward entries | Forwards host ports to container ports. Useful for rootless containers that cannot bind to privileged ports (< 1024). See [Firewall port forwarding](#firewall-port-forwarding). |
| **podman_quadlet_pre_pull_images** <br> boolean / default: `true` | Pre-pull container images before the first systemd restart. Parses `Image=` lines from deployed `.container` quadlet files and runs `podman pull` for each unique image. Prevents systemd `TimeoutStartSec` from expiring on first deploy. See [Image pre-pulling](#image-pre-pulling). |
| **podman_quadlet_pull_policy** <br> string / default: `newer` | `--policy` passed to `podman pull` during pre-pull. `newer` (default) re-downloads layers only when the remote is newer, saving bandwidth on redeploys. Other values: `always`, `missing`, `never`. See [Pull policy and registry-failure handling](#pull-policy-and-registry-failure-handling). |

### Config patching

Some containers create their own config files on first start. Instead of replacing these files entirely, you can patch specific values using `podman_quadlet_volumes_config_patches`. This is applied after the container has started once (creating the default config) and been stopped.

Supported formats: `yaml`, `json`, `ini`, `xml`, `keyvalue`.

```yaml
podman_quadlet_volumes_config_patches:
  - name: myapp-config
    patches:
      - file: config/settings.yml
        format: yaml
        owner: 1000
        group: 1000
        set:
          server.port: 8096
          server.host: "0.0.0.0"
      - file: config/app.ini
        format: ini
        section: database
        set:
          host: localhost
          port: "5432"
      - file: config/app.xml
        format: xml
        xpath_patches:
          - xpath: /config/server/port
            value: "8096"
      - file: config/app.env
        format: keyvalue
        delimiter: "="
        set:
          LOG_LEVEL: debug
```

For rootless containers, `owner` and `group` are container-perspective UIDs/GIDs (same as for volume file staging). For rootful containers, they are host UIDs/GIDs.

### Firewall port forwarding

Rootless containers cannot bind to privileged ports (< 1024). Use `podman_quadlet_firewall_port_forwards` to forward host ports to the container's higher-numbered ports via firewalld:

```yaml
podman_quadlet_firewall_port_forwards:
  - port: 443
    proto: tcp
    toport: 8443
  - port: 53
    proto: udp
    toport: 1053
```

This automatically detects the active firewalld zone and applies the forwarding rules.

### Image pre-pulling

On first deploy, the systemd quadlet unit tries to pull the container image during startup. If the image is large (e.g., ~1 GB) and the connection is slow, the pull can exceed the unit's `TimeoutStartSec`, causing the service to fail. For pod-based services with `exit-policy=stop`, one container timing out tears down the entire pod.

By default, the role pre-pulls all container images **before** the first systemd restart. It parses `Image=` lines from the deployed `.container` quadlet files and runs `podman pull` for each unique image. This ensures images are cached locally before systemd tries to start them.

- **Enabled by default** — set `podman_quadlet_pre_pull_images: false` to skip
- **Automatic** — no need to list images manually; the role discovers them from the quadlet files it just deployed
- **Rootless-aware** — pulls as the rootless user with the correct `XDG_RUNTIME_DIR`
- **Idempotent** — subsequent runs are fast no-ops when images are already cached

#### Pull policy and registry-failure handling

The pre-pull step uses `podman pull --policy={{ podman_quadlet_pull_policy }}` (default `newer`). With `newer`, podman consults the registry's manifest and only re-downloads layers that have actually changed upstream — an already-up-to-date image triggers no blob traffic.

Accepted `podman_quadlet_pull_policy` values (passed through to `podman pull --policy`):

| Value | Behaviour |
| --- | --- |
| `always` | Always pull, re-downloading unchanged layers. |
| `missing` | Pull only when the image is not already local; no registry consultation after that. |
| `newer` (default) | Pull only when the remote manifest is strictly newer than the local copy. |
| `never` | Never pull; fail if the image is not already cached locally. |

**Registry-failure fallback.** If the pull fails for any reason (rate limit, transient DNS, network outage) **and** the image is already present locally, the role logs a warning and continues with the cached image rather than failing the play. If the pull fails **and** no cached image exists (fresh install, rate-limited), the play hard-fails — there's nothing to fall back to. This makes redeploys resilient to transient registry problems without silently diverging on a clean install.

### Rootless UID/GID mapping

Rootless Podman containers use Linux user namespaces. The host user (e.g., UID 1005) maps to **UID 0 (root) inside the container**. Non-root container UIDs are mapped to high-numbered host UIDs via the subuid/subgid ranges in `/etc/subuid` and `/etc/subgid`.

| Inside container | Host (rootless user UID 1005, subuid start 100000) |
| --- | --- |
| UID 0 (root) | UID 1005 (the rootless host user) |
| UID 33 (www-data) | UID 100032 |
| UID 999 | UID 100998 |

When deploying files into rootless volumes, `owner` and `group` are **container-perspective UIDs/GIDs**. The role uses `podman unshare chown` to map them correctly through Podman's user namespace. You never need to calculate host subuid offsets yourself.

For **rootful** containers, `owner` and `group` are standard host UIDs/GIDs (no namespace remapping applies).

**Example:** deploying a config file owned by `www-data` (UID 33) inside a rootless container:

```yaml
podman_quadlet_volumes_files_to_stage:
  - name: myapp-config
    files:
      - src: app.conf
        owner: 33
        group: 33
        mode: "0644"
```

### Technical limitation: rootless volume ownership and subuid/subgid ranges

The UID/GID mapping for rootless containers is determined by the user's entry in `/etc/subuid` and `/etc/subgid`. These ranges are allocated sequentially when users are created (e.g., first user gets `524288:65536`, second gets `589824:65536`, etc.). The files stored in rootless volumes use **host-mapped UIDs** on disk.

This means:
- **As long as the Linux system user exists**, the subuid/subgid mapping remains stable and volume data keeps the correct ownership. You can freely stop, remove, and redeploy containers without issues.
- **If you delete the system user** (which removes the subuid/subgid entry) **but keep the volume data**, and then recreate the user, the new user will likely receive a different subuid range. The existing volume files will then have host UIDs from the old range, resulting in permission mismatches.

In practice this is rarely an issue: on a fresh server reinstall, volumes are either empty or should be restored using `podman unshare podman volume import`, which writes container-perspective UIDs that are correctly mapped through the new subuid range.

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
        - nginxrootless.container
        - nginxrootless.volume
      podman_quadlet_volumes_files_to_stage:
        - name: nginxrootless
          files:
            - src: index.html
      podman_quadlet_firewall_ports:
        - 8080/tcp

```

As a minimum configuration, you need to have the quadlet unit file `{{ playbook_dir }}/files/quadlets/nginxrootless.container` with the following content:
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

And a quadlet volume file `{{ playbook_dir }}/files/quadlets/nginxrootless.volume`
```
[Volume]
```

And the html file `{{ playbook_dir }}/files/volumes/nginxrootless/index.html`
```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
html { color-scheme: light dark; }
body { width: 35em; margin: 0 auto;
font-family: Tahoma, Verdana, Arial, sans-serif; }
</style>
</head>
<body>
<h1>Welcome to nginx rootless container test page!</h1>
<p>If you see this page, the nginx web server is successfully installed as rootless container and
working.</p>
</body>
</html>
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
      podman_quadlet_firewall_ports:
        - 80/tcp
```

As a minimum configuration, you need to have the quadlet unit file `{{ playbook_dir }}/files/quadlets/nginxrootful.container` with the following content:
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

And a quadlet volume file `{{ playbook_dir }}/files/quadlets/nginxrootful.volume`
```
[Volume]
```

And the html file `{{ playbook_dir }}/files/volumes/nginxrootful/index.html`
```html
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
html { color-scheme: light dark; }
body { width: 35em; margin: 0 auto;
font-family: Tahoma, Verdana, Arial, sans-serif; }
</style>
</head>
<body>
<h1>Welcome to nginx rootful container test page!</h1>
<p>If you see this page, the nginx web server is successfully installed as rootful container and
working.</p>
</body>
</html>
```

## How to execute molecule tests

### Install molecule

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

### Run tests

```bash
molecule reset && rm -rf ~/.cache/molecule && molecule test
```
