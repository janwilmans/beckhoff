# ADS Administration Tool

A small, dependency-free Python command-line tool for administering **Beckhoff TwinCAT PLCs over ADS**.

> Disclaimer:
> This is an independent, community-developed project.
> I have no affiliation with Beckhoff Automation GmbH, and this tool is not developed, endorsed, certified, or officially supported by Beckhoff.

The tool is intended for Linux-based automation and factory environments where PLCs need to be discovered, configured, backed up, restored, or switched between TwinCAT **Config** and **Run** mode without requiring the TwinCAT engineering environment.

It communicates directly with the Beckhoff ADS system services using standard Python sockets. No external Python packages are required.

## Features

* 🔎 **Discover PLCs** on the local network using ADS UDP discovery
* 🔗 **Add an ADS route** to a PLC
* ⚙️ Switch TwinCAT between **Config** and **Run** mode
* 💾 **Back up** the PLC boot project to a ZIP archive
* 📦 **Restore** a boot project from a ZIP archive
* 🐧 Supports PLC boot-project locations for:

  * TwinCAT/Linux
  * TwinCAT/BSD
  * Windows-based TwinCAT
* 📋 Produces machine-readable **JSON output**
* 🔐 Prompts for the PLC password instead of requiring it on the command line
* 🛡️ Validates ZIP contents before restoring them
* 🚫 Uses only Python's standard library

---

## Requirements

### Host

The tool currently expects a Linux host with:

* Python 3
* IPv4 networking
* the `ip` command from `iproute2`

For example:

```bash
python3 --version
ip -4 addr
```

### PLC

The PLC must expose the relevant Beckhoff ADS services on the network.

The tool uses:

| Service        |           Port | Purpose                                                  |
| -------------- | -------------: | -------------------------------------------------------- |
| ADS discovery  |      UDP 48899 | PLC discovery, AMS Net ID discovery and route management |
| ADS/TCP        |      TCP 48898 | ADS communication                                        |
| System service | AMS port 10000 | PLC administration and file access                       |

---

## Usage

The general syntax is:

```bash
./ads-admin.py ACTION [OPTIONS]
```

The available actions are:

```text
--scan
--add-route NAME ADDRESS [AMS-NET-ID]
--config
--run
--backup ZIP
--restore ZIP
```

For a complete list of options:

```bash
./ads-admin.py --help
```

---

## Discover PLCs

Use `--scan` to discover Beckhoff devices reachable through the host's IPv4 interfaces:

```bash
./ads-admin.py --scan
```

The tool sends ADS discovery requests to the broadcast address of each broadcast-capable IPv4 interface and also to the global IPv4 broadcast address.

The result is printed as JSON:

```json
{
    "protocol": "beckhoff-ads",
    "port": 48899,
    "deviceCount": 1,
    "devices": [
        {
            "address": "192.168.1.20",
            "amsNetId": "192.168.1.20.1.1",
            "amsPort": 851,
            "hostName": "PLC01",
            "osVersion": "12.0.0 (Linux)",
            "twincatVersion": "3.1.4024",
            "routeName": "PLC01"
        }
    ]
}
```

The exact fields depend on the information returned by the PLC.

This makes `--scan` useful for automatically finding PLCs before performing administration tasks.

### Custom timeout

The default timeout is 2 seconds:

```bash
./ads-admin.py --scan --timeout 5
```

---

# Add an ADS Route

An ADS route allows the PLC to communicate with an ADS client on another computer.

Use:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --add-route HAMILTON250 192.168.1.10
```

The arguments are:

```text
--add-route NAME ADDRESS [AMS-NET-ID]
```

where:

* `NAME` is the route name shown by TwinCAT
* `ADDRESS` is the IP address of the client computer
* `AMS-NET-ID` is optional

If the AMS Net ID is omitted, it defaults to:

```text
<client-ip>.1.1
```

For example:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --add-route HAMILTON250 192.168.1.10
```

implicitly creates the route:

```text
Name:     HAMILTON250
Address:  192.168.1.10
AMS Net ID: 192.168.1.10.1.1
```

If required, specify the AMS Net ID explicitly:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --add-route HAMILTON250 192.168.1.10 192.168.1.10.1.1
```

### Authentication

The default PLC account is:

```text
Administrator
```

If no password is specified, the tool securely prompts for it:

```text
Password for Administrator@192.168.1.20:
```

You can specify another username:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --username MyUser \
    --add-route HAMILTON250 192.168.1.10
```

A password can also be supplied with `--password`, although interactive prompting is preferable because command-line arguments may be visible to other users or process-monitoring tools.

---

# Switch TwinCAT to Config Mode

To put the PLC into TwinCAT Config mode:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --config
```

The command obtains the PLC's AMS Net ID automatically and sends the appropriate ADS state-change command.

A successful operation produces JSON similar to:

```json
{
    "address": "192.168.1.20",
    "amsNetId": "192.168.1.20.1.1",
    "command": "config",
    "source": {
        "amsNetId": "192.168.1.10.1.1"
    },
    "status": "acknowledged"
}
```

---

# Switch TwinCAT to Run Mode

To switch the PLC back to Run mode:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --run
```

The tool handles the expected ADS behaviour during the transition, where the ADS target port may temporarily disappear while TwinCAT changes state.

---

# Back Up a PLC

A PLC boot project can be downloaded to a local ZIP archive:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --backup plc-backup.zip
```

The tool:

1. Discovers the PLC and its AMS Net ID.
2. Determines the appropriate TwinCAT boot-project directory.
3. Recursively finds the boot-project files.
4. Downloads the files through ADS.
5. Stores them in a ZIP archive.

The resulting archive has the following general structure:

```text
plc-backup.zip
└── Plc/
    ├── ...
    └── ...
```

The backup will not overwrite an existing file:

```text
Backup file 'plc-backup.zip' already exists
```

This is intentional to prevent accidentally destroying an existing backup.

### Example

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --backup backups/plc-2026-09-16.zip
```

The result includes the number of files and total transferred size:

```json
{
    "address": "192.168.1.20",
    "amsNetId": "192.168.1.20.1.1",
    "command": "backup",
    "fileCount": 12,
    "size": 48321,
    "source": "/etc/TwinCAT/3.1/Boot/Plc",
    "status": "created",
    "target": "backups/plc-2026-09-16.zip"
}
```

---

# Restore a PLC

A previously created boot-project ZIP can be restored with:

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --restore plc-backup.zip
```

The restore process is:

```text
PLC
 │
 ├── switch TwinCAT → Config
 │
 ├── validate ZIP
 │
 ├── upload boot-project files
 │
 └── switch TwinCAT → Run
```

The tool determines the correct destination directory from the PLC's operating system.

For example:

### TwinCAT/Linux

```text
/etc/TwinCAT/3.1/Boot/Plc
```

### TwinCAT/BSD

```text
/usr/local/etc/TwinCAT/3.1/Boot/Plc
```

### Windows / TwinCAT

Depending on the TwinCAT version:

```text
C:/TwinCAT/3.1/Boot/Plc
```

or:

```text
C:/ProgramData/Beckhoff/TwinCAT/3.1/Boot/Plc
```

If the upload fails, the tool deliberately leaves TwinCAT in **Config mode** rather than automatically pretending that the restore succeeded.

This makes a failed restore visible and avoids silently running a partially restored project.

---

# ZIP Validation

Restore archives are validated before files are uploaded.

The tool rejects, among other things:

* encrypted ZIP entries
* symbolic links
* absolute paths
* Windows-style path separators
* `..` path components
* duplicate paths
* corrupt ZIP entries
* empty archives

This prevents an archive from writing files outside the intended PLC boot-project directory.

The tool also accepts archives containing an enclosing `Plc` directory, making it directly compatible with archives produced by `--backup`.

---

# Automating PLC Deployment

The JSON output makes the tool suitable for scripts and factory automation.

For example:

```bash
./ads-admin.py \
    --ipaddress "$PLC_IP" \
    --backup "$BACKUP_FILE"
```

The output can be consumed directly by another program:

```bash
result=$(./ads-admin.py \
    --ipaddress "$PLC_IP" \
    --backup "$BACKUP_FILE")
```

Because normal command output is JSON, the tool can also be integrated into Python, Bash, CI/CD pipelines, or larger PLC deployment tooling.

A typical automated workflow could be:

```text
Discover PLC
     │
     ▼
Determine IP / AMS Net ID
     │
     ▼
Add ADS route
     │
     ▼
Backup existing PLC
     │
     ▼
Switch to Config
     │
     ▼
Restore new boot project
     │
     ▼
Switch to Run
```

---

# Network Behaviour

The tool implements the required ADS protocol messages itself using Python's standard `socket`, `struct`, and related modules.

Discovery uses:

```text
UDP 48899
```

ADS communication uses:

```text
TCP 48898
```

The discovery mechanism sends requests using the broadcast addresses of the host's IPv4 interfaces. This is useful in environments where PLCs use static addresses or link-local addressing and there is no DHCP-based device discovery.

For operations against a known PLC, the tool communicates directly with its IP address.

---

# AMS Net IDs

An AMS Net ID consists of six decimal components:

```text
192.168.1.20.1.1
```

The tool validates that every component is in the range `0..255`.

When an AMS Net ID is not supplied for a new route, the default is:

```text
<IP address>.1.1
```

For example:

```text
IP address:  192.168.1.10
AMS Net ID:  192.168.1.10.1.1
```

---

# Options

The complete command-line interface is:

```text
--scan, -s
    Scan for devices using UDP broadcast

--add-route NAME ADDRESS [AMS-NET-ID]
    Add an ADS route to the PLC

--config
    Set TwinCAT on the PLC to Config mode

--run
    Set TwinCAT on the PLC to Run mode

--backup ZIP
    Back up the TwinCAT PLC boot project to a ZIP

--restore ZIP
    Restore a TwinCAT PLC boot-project ZIP

--ipaddress PLC-IP
    IP address of the PLC to administrate

--username USERNAME
    PLC administrator account
    Default: Administrator

--password PASSWORD
    PLC account password

--timeout SECONDS
    Seconds to wait for replies
    Default: 2
```

Exactly one of the primary actions must be selected.

All actions except `--scan` require `--ipaddress`.

---

# Examples

## Find all PLCs

```bash
./ads-admin.py --scan
```

## Add this computer as an ADS route

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --add-route HAMILTON250 192.168.1.10
```

## Enter Config mode

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --config
```

## Return to Run mode

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --run
```

## Back up the PLC

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --backup plc-backup.zip
```

## Restore a PLC

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --restore plc-backup.zip
```

## Use a longer timeout

```bash
./ads-admin.py \
    --ipaddress 192.168.1.20 \
    --timeout 10 \
    --backup plc-backup.zip
```

---

# Design

The tool deliberately has no dependency on the Beckhoff ADS Python package.

Instead, it implements the small subset of ADS system services needed for administration:

```text
                 ┌─────────────────────┐
                 │    ads-admin.py      │
                 └──────────┬──────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       UDP discovery    ADS/TCP        System service
          :48899          :48898          AMS :10000
             │              │              │
             └──────────────┼──────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Beckhoff PLC  │
                    │    TwinCAT    │
                    └───────────────┘
```

This keeps the tool small and makes it possible to use it on a minimal Linux installation without installing a larger ADS SDK.

---

# Security Considerations

This tool performs administrative operations on a PLC, including:

* adding ADS routes
* changing TwinCAT state
* reading the PLC boot project
* writing the PLC boot project

Use it only on trusted networks and with appropriate PLC credentials.

In particular, avoid putting passwords directly on the command line when possible:

```bash
# Prefer
./ads-admin.py --ipaddress 192.168.1.20 --add-route ...

# Rather than
./ads-admin.py --ipaddress 192.168.1.20 --password secret ...
```

When `--password` is omitted, the tool prompts interactively.

The ADS messages implemented by this tool are intended for PLC administration. This tool should not be treated as a general-purpose secure remote-management protocol.

---

# Error Handling

Expected operational errors are reported without a Python traceback.

For example:

```text
PLC 192.168.1.20 did not respond
```

or:

```text
PLC rejected the username or password
```

Unexpected programming or runtime errors produce a traceback to aid debugging.

The process exits with a non-zero status on failure, making it suitable for use in automation:

```bash
./ads-admin.py --ipaddress "$PLC_IP" --restore "$BACKUP"

if [ $? -ne 0 ]; then
    echo "PLC restore failed"
    exit 1
fi
```

---

# Limitations

This is a focused administration tool rather than a complete ADS client.

It currently implements the functionality required for:

* ADS discovery
* AMS Net ID discovery
* ADS route creation
* TwinCAT state changes
* PLC boot-project file transfer
* PLC boot-project backup and restore

It does not attempt to implement general PLC variable access, symbol browsing, PLC program execution, or a full ADS client API.

---

# License

MIT License

Copyright (c) 2026 Jan Wilmans

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
