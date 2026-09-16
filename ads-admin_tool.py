#!/usr/bin/env python3

import argparse
import getpass
import ipaddress
import json
import re
import socket
import struct
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ADS_DISCOVERY_PORT = 48899
ADS_HEADER = b"\x03\x66\x14\x71"
ADS_SERVICE_DISCOVERY = 0x00000001
ADS_SERVICE_ADD_ROUTE = 0x00000006
ADS_RESPONSE_FLAG = 0x80000000
ADS_PORT_SYSTEMSERVICE = 10000
ADS_COMMAND_WRITE = 5
AMS_TCP_PORT = 48898
AMS_TCP_HEADER_LENGTH = 6
AMS_HEADER_LENGTH = 32
AMS_SOURCE_PORT = 32768
AMS_COMMAND_WRITE_CONTROL = 5
AMS_COMMAND_READ_WRITE = 9
AMS_STATE_FLAGS_REQUEST = 4
AMS_STATE_FLAGS_RESPONSE = 5
ADS_STATE_RESET = 2
ADS_STATE_RECONFIG = 16
ADS_DEVICE_STATE = 0
WRITE_CONTROL_RESPONSE_SIZE = AMS_TCP_HEADER_LENGTH + AMS_HEADER_LENGTH + 4
AMS_NET_ID_LENGTH = 6
BLOCK_PASSWORD = 0x0002
ADD_ROUTE_RESPONSE_MIN_SIZE = 29
BROADCAST_ADDRESS = "255.255.255.255"
SYSTEMSERVICE_FOPEN = 120
SYSTEMSERVICE_FCLOSE = 121
SYSTEMSERVICE_FREAD = 122
SYSTEMSERVICE_FWRITE = 123
SYSTEMSERVICE_FFILEFIND = 133
FOPEN_READ_BINARY = (1 << 0) | (1 << 4) | (1 << 6)
FOPEN_WRITE_BINARY = (1 << 1) | (1 << 3) | (1 << 4) | (1 << 6)
ADS_FILE_CHUNK_SIZE = 64 * 1024
MAX_AMS_RESPONSE_SIZE = 16 * 1024 * 1024
ADS_ERROR_FILE_NOT_FOUND = 1804
FILE_FIND_DATA_SIZE = 324
FILE_ATTRIBUTE_DIRECTORY = 0x10
FILE_FIND_NAME_OFFSET = 48
FILE_FIND_NAME_SIZE = 260

# Data blocks of a discovery reply, each block is: uint16 type, uint16 length, length bytes of data.
BLOCK_STATUS = 0x0001
BLOCK_TWINCAT_VERSION = 0x0003
BLOCK_OS_VERSION = 0x0004
BLOCK_HOST_NAME = 0x0005
BLOCK_AMS_NET_ID = 0x0007
BLOCK_OPTIONS = 0x0009
BLOCK_ROUTE_NAME = 0x000C
BLOCK_USER_NAME = 0x000D
BLOCK_FINGERPRINT = 0x0012

BLOCK_NAMES = {
    BLOCK_STATUS: "status",
    BLOCK_TWINCAT_VERSION: "twincatVersion",
    BLOCK_HOST_NAME: "hostName",
    BLOCK_OS_VERSION: "osVersion",
    BLOCK_AMS_NET_ID: "amsNetId",
    BLOCK_OPTIONS: "options",
    BLOCK_ROUTE_NAME: "routeName",
    BLOCK_USER_NAME: "userName",
    BLOCK_FINGERPRINT: "fingerprint",
}


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def sprint(*args, **kwargs):
    print(*args, file=sys.stdout, **kwargs)
    sys.stdout.flush()


def create_args_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--scan", "-s", action="store_true", help="Scan for devices using UDP broadcast")
    actions.add_argument("--add-route", nargs="+", metavar="ARG", help="Add route NAME ADDRESS [AMS-NET-ID] to the PLC")
    actions.add_argument("--config", action="store_true", help="Set TwinCAT on the PLC to Config mode")
    actions.add_argument("--run", action="store_true", help="Set TwinCAT on the PLC to Run mode")
    actions.add_argument("--backup", metavar="ZIP", help="Back up the TwinCAT PLC boot project to a ZIP")
    actions.add_argument("--restore", metavar="ZIP", help="Restore a TwinCAT PLC boot-project ZIP")
    parser.add_argument("--ipaddress", "--ipaddres", metavar="PLC-IP", help="IP address of the PLC to administrate")
    parser.add_argument("--username", default="Administrator", help="PLC administrator account (default: Administrator)")
    parser.add_argument("--password", help="PLC account password (prompted when omitted)")
    parser.add_argument("--timeout", "-t", type=float, default=2.0, help="Seconds to wait for replies (default: 2)")
    return parser


# This is a "something is wrong and I can explain" exception,
# which we catch and treat differently from generic exceptions
# which will print a traceback.
class ExplainException(Exception):
    def __init__(self, s):
        self.message = s


@dataclass(frozen=True)
class AdsRoute:
    name: str
    address: str
    ams_net_id: str

    @classmethod
    def create(cls, name, address, ams_net_id=None):
        address = as_ipv4_address(address)
        return cls(name, address, ams_net_id or f"{address}.1.1")


@dataclass(frozen=True)
class BootProjectFile:
    archive_name: str
    relative_path: str
    size: int


def as_ams_net_id(data):
    return ".".join(str(value) for value in data)


def to_ams_net_id(ams_net_id):
    try:
        values = [int(value) for value in ams_net_id.split(".")]
    except ValueError as error:
        raise ExplainException(f"{ams_net_id!r} is not a valid AmsNetId") from error
    if len(values) != AMS_NET_ID_LENGTH or any(value < 0 or value > 255 for value in values):
        raise ExplainException(f"{ams_net_id!r} is not a valid AmsNetId")
    return bytes(values)


def as_ipv4_address(address):
    try:
        return str(ipaddress.IPv4Address(address))
    except ipaddress.AddressValueError as error:
        raise ExplainException(f"{address!r} is not a valid IPv4 address") from error


def get_interface_networks():
    """
    Returns the (address, broadcast address) pairs of all broadcast capable IPv4 interfaces.
    """
    result = subprocess.run(["ip", "-o", "-4", "addr", "show"], capture_output=True, text=True)
    networks = []
    for match in re.finditer(r"inet (\d+\.\d+\.\d+\.\d+/\d+)", result.stdout):
        network = ipaddress.IPv4Network(match.group(1), strict=False)
        address = ipaddress.IPv4Address(match.group(1).split("/")[0])
        if network.prefixlen == 32 or address.is_loopback:
            continue
        networks += [(str(address), str(network.broadcast_address))]
    return networks


def make_header(service_id):
    return ADS_HEADER + struct.pack("<II", 0, service_id)


def make_request(ams_net_id):
    """
    Builds a discovery request as sent by the TwinCAT router, without any data blocks.
    """
    message = make_header(ADS_SERVICE_DISCOVERY)
    message += to_ams_net_id(ams_net_id)
    message += struct.pack("<H", ADS_PORT_SYSTEMSERVICE)
    message += struct.pack("<I", 0)
    return message


def make_add_route_request(route_name, route_address, ams_net_id, username, password):
    """Builds a TwinCAT system-service request that adds a route to the PLC."""
    route_name = route_name.encode("utf-8") + b"\0"
    route_address = route_address.encode("utf-8") + b"\0"
    username = username.encode("utf-8") + b"\0"
    password = password.encode("utf-8") + b"\0"

    message = make_header(ADS_SERVICE_ADD_ROUTE)
    message += to_ams_net_id(ams_net_id)
    message += struct.pack("<HH", ADS_PORT_SYSTEMSERVICE, ADS_COMMAND_WRITE)
    message += b"\x00\x00\x0c\x00"
    message += struct.pack("<H", len(route_name)) + route_name
    message += struct.pack("<HH", BLOCK_AMS_NET_ID, AMS_NET_ID_LENGTH)
    message += to_ams_net_id(ams_net_id)
    message += struct.pack("<HH", BLOCK_USER_NAME, len(username)) + username
    message += struct.pack("<HH", BLOCK_PASSWORD, len(password)) + password
    message += struct.pack("<HH", BLOCK_HOST_NAME, len(route_address)) + route_address
    return message


def make_write_control_request(target_ams_net_id, source_ams_net_id, ads_state):
    """Builds an ADS WriteControl request for the TwinCAT system service."""
    data = struct.pack("<HHI", ads_state, ADS_DEVICE_STATE, 0)
    header = to_ams_net_id(target_ams_net_id) + struct.pack("<H", ADS_PORT_SYSTEMSERVICE)
    header += to_ams_net_id(source_ams_net_id) + struct.pack("<H", AMS_SOURCE_PORT)
    header += struct.pack("<HHIII", AMS_COMMAND_WRITE_CONTROL, AMS_STATE_FLAGS_REQUEST, len(data), 0, 1)
    return struct.pack("<HI", 0, len(header) + len(data)) + header + data


def make_ams_request(target_ams_net_id, source_ams_net_id, command, payload, invoke_id):
    """Builds a routed AMS/TCP request."""
    header = to_ams_net_id(target_ams_net_id) + struct.pack("<H", ADS_PORT_SYSTEMSERVICE)
    header += to_ams_net_id(source_ams_net_id) + struct.pack("<H", AMS_SOURCE_PORT)
    header += struct.pack("<HHIII", command, AMS_STATE_FLAGS_REQUEST, len(payload), 0, invoke_id)
    return struct.pack("<HI", 0, len(header) + len(payload)) + header + payload


def parse_write_control_response(data):
    """Validates an ADS WriteControl response and raises for an ADS error."""
    if len(data) < WRITE_CONTROL_RESPONSE_SIZE:
        raise ExplainException("PLC returned an invalid ADS WriteControl response")
    tcp_reserved, tcp_length = struct.unpack_from("<HI", data)
    command, flags = struct.unpack_from("<HH", data, AMS_TCP_HEADER_LENGTH + 16)
    if tcp_reserved or tcp_length != len(data) - AMS_TCP_HEADER_LENGTH:
        raise ExplainException("PLC returned an invalid AMS/TCP response")
    if command != AMS_COMMAND_WRITE_CONTROL or flags != AMS_STATE_FLAGS_RESPONSE:
        raise ExplainException("PLC returned an unexpected ADS response")
    ads_error = struct.unpack_from("<I", data, AMS_TCP_HEADER_LENGTH + 24)[0]
    result = struct.unpack_from("<I", data, AMS_TCP_HEADER_LENGTH + AMS_HEADER_LENGTH)[0]
    if ads_error or result:
        raise ExplainException(f"PLC returned ADS error {ads_error or result}")


def parse_add_route_response(data):
    expected_service = ADS_SERVICE_ADD_ROUTE | ADS_RESPONSE_FLAG
    if len(data) < ADD_ROUTE_RESPONSE_MIN_SIZE or data[:4] != ADS_HEADER:
        raise ExplainException("PLC returned an invalid add-route response")
    if struct.unpack_from("<I", data, 8)[0] != expected_service:
        raise ExplainException("PLC returned an unexpected system-service response")
    status = data[26:29]
    if status == b"\x04\x00\x00":
        return as_ams_net_id(data[12:18])
    if status == b"\x00\x04\x07":
        raise ExplainException("PLC rejected the username or password")
    raise ExplainException(f"PLC rejected the route request (status {status.hex()})")


def decode_string(data):
    return data.split(b"\0")[0].decode("utf-8", errors="replace")


def decode_twincat_version(data):
    if len(data) < 4:
        return data.hex()
    major, minor, build = struct.unpack_from("<BBH", data, 0)
    return f"{major}.{minor}.{build}"


def decode_os_version(data):
    if len(data) < 20:
        return data.hex()
    _, major, minor, build, platform_id = struct.unpack_from("<IIIII", data, 0)
    platforms = {0: "Linux", 1: "TC/RTOS", 2: "Windows NT", 3: "Windows CE"}
    platform = platforms.get(platform_id, f"platform {platform_id}")
    version_info = data[20:]
    if platform_id in (0, 1):
        service_pack = decode_string(version_info)
    else:
        characters = struct.iter_unpack("<H", version_info[: len(version_info) // 2 * 2])
        service_pack = "".join(chr(value) for (value,) in characters if value)
    suffix = f", {service_pack}" if service_pack and service_pack != platform else ""
    return f"{major}.{minor}.{build} ({platform}{suffix})"


def decode_block(block_type, data):
    if block_type in (BLOCK_HOST_NAME, BLOCK_FINGERPRINT, BLOCK_ROUTE_NAME, BLOCK_USER_NAME):
        return decode_string(data)
    if block_type == BLOCK_TWINCAT_VERSION:
        return decode_twincat_version(data)
    if block_type == BLOCK_OS_VERSION:
        return decode_os_version(data)
    if block_type == BLOCK_AMS_NET_ID:
        return as_ams_net_id(data[:6])
    if block_type in (BLOCK_STATUS, BLOCK_OPTIONS) and len(data) >= 4:
        return struct.unpack_from("<I", data)[0]
    return data.hex()


def parse_blocks(data, offset, count):
    result = {}
    for _ in range(count):
        if offset + 4 > len(data):
            break
        block_type, length = struct.unpack_from("<HH", data, offset)
        offset += 4
        if offset + length > len(data):
            break
        name = BLOCK_NAMES.get(block_type, f"block{block_type:#06x}")
        result[name] = decode_block(block_type, data[offset : offset + length])
        offset += length
    return result


def parse_message(data):
    """
    Returns (service_id, device) for a discovery message, or (None, None) if @p data is not one.
    """
    if len(data) < 24 or data[0:4] != ADS_HEADER:
        return (None, None)

    service_id = struct.unpack_from("<I", data, 8)[0]
    ams_port = struct.unpack_from("<H", data, 18)[0]
    block_count = struct.unpack_from("<I", data, 20)[0]
    device = {
        "amsNetId": as_ams_net_id(data[12:18]),
        "amsPort": ams_port,
    }
    device.update(parse_blocks(data, 24, block_count))
    return (service_id, device)


def scan(timeout):
    """
    Broadcasts a discovery request on every IPv4 interface and reports the replying devices.
    """
    devices = {}
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_socket.bind(("0.0.0.0", 0))
    try:
        for address, broadcast in get_interface_networks():
            udp_socket.sendto(make_request(f"{address}.1.1"), (broadcast, ADS_DISCOVERY_PORT))
        udp_socket.sendto(make_request("1.1.1.1.1.1"), (BROADCAST_ADDRESS, ADS_DISCOVERY_PORT))

        udp_socket.settimeout(timeout)
        start_time = time.monotonic()
        while (time.monotonic() - start_time) < timeout:
            try:
                data, sender = udp_socket.recvfrom(4096)
            except TimeoutError:
                break
            service_id, device = parse_message(data)
            if device is None or service_id & ADS_RESPONSE_FLAG == 0:
                continue
            device["address"] = sender[0]
            # a device replies to the broadcast on every interface it is reachable on
            devices[(device["address"], device["amsNetId"])] = device
    finally:
        udp_socket.close()

    result = {
        "protocol": "beckhoff-ads",
        "port": ADS_DISCOVERY_PORT,
        "deviceCount": len(devices),
        "devices": list(devices.values()),
    }
    sprint(json.dumps(result, indent=4, sort_keys=True))
    return 0


def add_route(plc_address, route, username, password, timeout):
    """Adds an ADS route to the PLC using its UDP system service."""
    plc_address = as_ipv4_address(plc_address)
    request = make_add_route_request(route.name, route.address, route.ams_net_id, username, password)

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(timeout)
        udp_socket.sendto(request, (plc_address, ADS_DISCOVERY_PORT))
        try:
            response, sender = udp_socket.recvfrom(4096)
        except TimeoutError as error:
            raise ExplainException(f"PLC {plc_address} did not respond") from error
    if sender[0] != plc_address:
        raise ExplainException(f"Received add-route response from unexpected host {sender[0]}")

    plc_ams_net_id = parse_add_route_response(response)
    result = {
        "address": plc_address,
        "amsNetId": plc_ams_net_id,
        "route": {"name": route.name, "address": route.address, "amsNetId": route.ams_net_id},
        "status": "added",
    }
    sprint(json.dumps(result, indent=4, sort_keys=True))
    return 0


def get_local_address(plc_address):
    """Returns the local interface address used to reach @p plc_address."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((plc_address, ADS_DISCOVERY_PORT))
        return probe.getsockname()[0]


def get_device(plc_address, timeout):
    """Asks one PLC for its discovery information."""
    request = make_request(f"{get_local_address(plc_address)}.1.1")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.settimeout(timeout)
        udp_socket.sendto(request, (plc_address, ADS_DISCOVERY_PORT))
        while True:
            try:
                data, sender = udp_socket.recvfrom(4096)
            except TimeoutError as error:
                raise ExplainException(f"PLC {plc_address} did not report its AmsNetId") from error
            service_id, device = parse_message(data)
            if device is not None and sender[0] == plc_address and service_id & ADS_RESPONSE_FLAG:
                device["address"] = sender[0]
                return device


def get_ams_net_id(plc_address, timeout):
    """Asks the PLC for its AmsNetId using the UDP discovery service."""
    return get_device(plc_address, timeout)["amsNetId"]


def receive_exactly(tcp_socket, length):
    data = b""
    while len(data) < length:
        chunk = tcp_socket.recv(length - len(data))
        if not chunk:
            break
        data += chunk
    return data


class RoutedAdsClient:
    """Minimal routed ADS client used by the TwinCAT system file service."""

    def __init__(self, plc_address, target_ams_net_id, source_ams_net_id, timeout):
        self.target_ams_net_id = target_ams_net_id
        self.source_ams_net_id = source_ams_net_id
        self.invoke_id = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        try:
            self.socket.connect((plc_address, AMS_TCP_PORT))
        except OSError:
            self.socket.close()
            raise

    def close(self):
        self.socket.close()

    def __enter__(self):
        return self

    def __exit__(self, _exception_type, _exception, _traceback):
        self.close()

    def request(self, command, payload):
        self.invoke_id += 1
        packet = make_ams_request(self.target_ams_net_id, self.source_ams_net_id, command, payload, self.invoke_id)
        self.socket.sendall(packet)
        tcp_header = receive_exactly(self.socket, AMS_TCP_HEADER_LENGTH)
        if len(tcp_header) != AMS_TCP_HEADER_LENGTH:
            raise ExplainException("PLC closed the ADS connection")
        reserved, length = struct.unpack("<HI", tcp_header)
        if reserved or length < AMS_HEADER_LENGTH or length > MAX_AMS_RESPONSE_SIZE:
            raise ExplainException("PLC returned an invalid AMS/TCP response")
        response = receive_exactly(self.socket, length)
        if len(response) != length:
            raise ExplainException("PLC returned a truncated ADS response")
        response_command, flags, data_length, ads_error, invoke_id = struct.unpack_from("<HHIII", response, 16)
        if response_command != command or flags != AMS_STATE_FLAGS_RESPONSE or invoke_id != self.invoke_id:
            raise ExplainException("PLC returned an unexpected ADS response")
        if data_length != len(response) - AMS_HEADER_LENGTH:
            raise ExplainException("PLC returned an invalid ADS response length")
        if ads_error:
            raise ExplainException(f"PLC returned ADS error {ads_error}")
        return response[AMS_HEADER_LENGTH:]

    def read_write_result(self, index_group, index_offset, read_length=0, write_data=b""):
        payload = struct.pack("<IIII", index_group, index_offset, read_length, len(write_data)) + write_data
        response = self.request(AMS_COMMAND_READ_WRITE, payload)
        if len(response) < 8:
            raise ExplainException("PLC returned an invalid ADS ReadWrite response")
        result, returned_length = struct.unpack_from("<II", response)
        returned_data = response[8:]
        if returned_length != len(returned_data) or returned_length > read_length:
            raise ExplainException("PLC returned an invalid ADS ReadWrite result")
        return result, returned_data

    def read_write(self, index_group, index_offset, read_length=0, write_data=b""):
        result, returned_data = self.read_write_result(index_group, index_offset, read_length, write_data)
        if result:
            raise ExplainException(f"PLC returned ADS error {result}")
        return returned_data

    def find_files(self, remote_directory):
        """Recursively returns (relative path, remote path) for regular files."""
        files = []
        pending = [("", remote_directory)]
        while pending:
            relative_directory, directory = pending.pop()
            children = self._find_children(directory)
            for name, is_directory in children:
                relative_path = f"{relative_directory}/{name}".lstrip("/")
                remote_path = f"{directory}/{name}"
                if is_directory:
                    pending.append((relative_path, remote_path))
                else:
                    files.append((relative_path, remote_path))
        return sorted(files)

    def _find_children(self, remote_directory):
        children = []
        result, data = self.read_write_result(SYSTEMSERVICE_FFILEFIND, 1, FILE_FIND_DATA_SIZE, f"{remote_directory}/*".encode())
        while result != ADS_ERROR_FILE_NOT_FOUND:
            if result:
                raise ExplainException(f"PLC returned ADS error {result}")
            if len(data) != FILE_FIND_DATA_SIZE:
                raise ExplainException("PLC returned invalid file information")
            handle, attributes = struct.unpack_from("<II", data)
            name_data = data[FILE_FIND_NAME_OFFSET : FILE_FIND_NAME_OFFSET + FILE_FIND_NAME_SIZE]
            name = decode_string(name_data)
            if not name or name in (".", "..") or "/" in name or "\\" in name:
                raise ExplainException(f"PLC returned an unsafe file name {name!r}")
            children.append((name, bool(attributes & FILE_ATTRIBUTE_DIRECTORY)))
            result, data = self.read_write_result(SYSTEMSERVICE_FFILEFIND, handle, FILE_FIND_DATA_SIZE)
        return children

    def download(self, remote_path, destination):
        handle_data = self.read_write(SYSTEMSERVICE_FOPEN, FOPEN_READ_BINARY, 4, remote_path.encode())
        if len(handle_data) != 4:
            raise ExplainException(f"PLC did not open {remote_path!r}")
        handle = struct.unpack("<I", handle_data)[0]
        size = 0
        try:
            while chunk := self.read_write(SYSTEMSERVICE_FREAD, handle, ADS_FILE_CHUNK_SIZE):
                destination.write(chunk)
                size += len(chunk)
        finally:
            self.read_write(SYSTEMSERVICE_FCLOSE, handle)
        return size

    def upload(self, remote_path, source):
        handle_data = self.read_write(SYSTEMSERVICE_FOPEN, FOPEN_WRITE_BINARY, 4, remote_path.encode())
        if len(handle_data) != 4:
            raise ExplainException(f"PLC did not open {remote_path!r}")
        handle = struct.unpack("<I", handle_data)[0]
        try:
            while chunk := source.read(ADS_FILE_CHUNK_SIZE):
                self.read_write(SYSTEMSERVICE_FWRITE, handle, write_data=chunk)
        finally:
            self.read_write(SYSTEMSERVICE_FCLOSE, handle)


def set_twincat_state(command, plc_address, ads_state, timeout, emit=True):
    """Changes the state of the remote TwinCAT system service."""
    plc_address = as_ipv4_address(plc_address)
    target_ams_net_id = get_ams_net_id(plc_address, timeout)
    source_ams_net_id = f"{get_local_address(plc_address)}.1.1"
    request = make_write_control_request(target_ams_net_id, source_ams_net_id, ads_state)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.settimeout(timeout)
        try:
            tcp_socket.connect((plc_address, AMS_TCP_PORT))
        except OSError as error:
            raise ExplainException(f"Cannot reach the ADS router of {plc_address}: {error}") from error
        try:
            tcp_socket.sendall(request)
            response = receive_exactly(tcp_socket, WRITE_CONTROL_RESPONSE_SIZE)
        except (ConnectionResetError, TimeoutError):
            response = b""
        except OSError as error:
            raise ExplainException(f"Cannot send ADS state command to {plc_address}: {error}") from error

    if response:
        try:
            parse_write_control_response(response)
        except ExplainException as error:
            # TwinCAT can return target-port-not-found while changing RUN/CONFIG state.
            if "ADS error 1861" not in error.message:
                raise
    result = {
        "address": plc_address,
        "amsNetId": target_ams_net_id,
        "command": command,
        "source": {"amsNetId": source_ams_net_id},
        "status": "acknowledged" if response else "sent",
    }
    if emit:
        sprint(json.dumps(result, indent=4, sort_keys=True))
    return 0


def config(plc_address, timeout):
    """Switches TwinCAT to Config mode using the RECONFIG command state."""
    return set_twincat_state("config", plc_address, ADS_STATE_RECONFIG, timeout)


def run(plc_address, timeout):
    """Switches TwinCAT to Run mode using the RESET command state."""
    return set_twincat_state("run", plc_address, ADS_STATE_RESET, timeout)


def inspect_boot_project_zip(zip_path):
    """Returns validated PLC boot files and strips one enclosing Plc directory."""
    try:
        archive = zipfile.ZipFile(zip_path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ExplainException(f"{str(zip_path)!r} is not a valid ZIP archive") from error
    with archive:
        entries = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            if info.flag_bits & 1:
                raise ExplainException("Encrypted ZIP entries are not supported")
            if info.external_attr >> 16 & 0o170000 == 0o120000:
                raise ExplainException(f"ZIP entry {info.filename!r} is a symbolic link")
            if "\\" in info.filename or info.filename.startswith("/"):
                raise ExplainException(f"Unsafe ZIP entry {info.filename!r}")
            parts = PurePosixPath(info.filename).parts
            if not parts or any(part in ("", ".", "..") for part in parts) or ":" in parts[0]:
                raise ExplainException(f"Unsafe ZIP entry {info.filename!r}")
            entries.append((info, parts))
        try:
            damaged_entry = archive.testzip()
        except (NotImplementedError, RuntimeError) as error:
            raise ExplainException(f"Cannot read the boot-project ZIP: {error}") from error
        if damaged_entry:
            raise ExplainException(f"ZIP entry {damaged_entry!r} failed its CRC check")
    if not entries:
        raise ExplainException("The boot-project ZIP contains no files")

    plc_prefixes = []
    for _info, parts in entries:
        positions = [index for index, part in enumerate(parts) if part.lower() == "plc"]
        plc_prefixes.append(parts[: positions[-1] + 1] if positions else None)
    prefix = plc_prefixes[0] if plc_prefixes and all(item == plc_prefixes[0] for item in plc_prefixes) else ()
    prefix = prefix or ()

    result = []
    seen = set()
    for info, parts in entries:
        relative_parts = parts[len(prefix) :]
        if not relative_parts:
            continue
        relative_path = "/".join(relative_parts)
        duplicate_key = relative_path.casefold()
        if duplicate_key in seen:
            raise ExplainException(f"Duplicate boot-project path {relative_path!r}")
        seen.add(duplicate_key)
        result.append(BootProjectFile(info.filename, relative_path, info.file_size))
    if not result:
        raise ExplainException("The boot-project ZIP contains no PLC boot files")
    return sorted(result, key=lambda entry: entry.relative_path)


def plc_boot_directory(device):
    """Returns the documented PLC boot directory for the discovered target."""
    operating_system = device.get("osVersion", "")
    if "Linux" in operating_system:
        return "/etc/TwinCAT/3.1/Boot/Plc"
    if "TwinCAT/BSD" in operating_system:
        return "/usr/local/etc/TwinCAT/3.1/Boot/Plc"
    if "Windows NT" in operating_system:
        try:
            build = int(device.get("twincatVersion", "0.0.4026").split(".")[2])
        except (IndexError, ValueError) as error:
            raise ExplainException("PLC reported an invalid TwinCAT version") from error
        if build < 4026:
            return "C:/TwinCAT/3.1/Boot/Plc"
        return "C:/ProgramData/Beckhoff/TwinCAT/3.1/Boot/Plc"
    raise ExplainException(f"Unsupported PLC operating system {operating_system!r}")


def restore(plc_address, zip_path, timeout):
    """Restores a TwinCAT PLC boot project and restarts TwinCAT in Run mode."""
    plc_address = as_ipv4_address(plc_address)
    zip_path = Path(zip_path)
    files = inspect_boot_project_zip(zip_path)
    device = get_device(plc_address, timeout)
    target_directory = plc_boot_directory(device)
    source_ams_net_id = f"{get_local_address(plc_address)}.1.1"

    set_twincat_state("config", plc_address, ADS_STATE_RECONFIG, timeout, emit=False)
    try:
        with RoutedAdsClient(plc_address, device["amsNetId"], source_ams_net_id, timeout) as client:
            with zipfile.ZipFile(zip_path) as archive:
                for entry in files:
                    with archive.open(entry.archive_name) as source:
                        client.upload(f"{target_directory}/{entry.relative_path}", source)
    except OSError as error:
        raise ExplainException(f"Cannot transfer the boot project to {plc_address}: {error}; TwinCAT remains in Config mode") from error
    except ExplainException as error:
        raise ExplainException(f"{error.message}; TwinCAT remains in Config mode") from error
    set_twincat_state("run", plc_address, ADS_STATE_RESET, timeout, emit=False)

    result = {
        "address": plc_address,
        "amsNetId": device["amsNetId"],
        "command": "restore",
        "fileCount": len(files),
        "size": sum(entry.size for entry in files),
        "source": str(zip_path),
        "status": "installed",
        "target": target_directory,
    }
    sprint(json.dumps(result, indent=4, sort_keys=True))
    return 0


def backup(plc_address, zip_path, timeout):
    """Backs up the remote TwinCAT PLC boot project to a local ZIP archive."""
    plc_address = as_ipv4_address(plc_address)
    zip_path = Path(zip_path)
    if zip_path.exists():
        raise ExplainException(f"Backup file {str(zip_path)!r} already exists")
    device = get_device(plc_address, timeout)
    source_directory = plc_boot_directory(device)
    source_ams_net_id = f"{get_local_address(plc_address)}.1.1"
    temporary_path = None
    total_size = 0
    try:
        with RoutedAdsClient(plc_address, device["amsNetId"], source_ams_net_id, timeout) as client:
            files = client.find_files(source_directory)
            if not files:
                raise ExplainException("The PLC boot-project directory contains no files")
            temporary = tempfile.NamedTemporaryFile(prefix=f".{zip_path.name}.", suffix=".tmp", dir=zip_path.parent, delete=False)
            temporary_path = Path(temporary.name)
            temporary.close()
            with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for relative_path, remote_path in files:
                    with archive.open(f"Plc/{relative_path}", "w") as destination:
                        total_size += client.download(remote_path, destination)
        temporary_path.rename(zip_path)
    except OSError as error:
        raise ExplainException(f"Cannot back up the boot project from {plc_address}: {error}") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    result = {
        "address": plc_address,
        "amsNetId": device["amsNetId"],
        "command": "backup",
        "fileCount": len(files),
        "size": total_size,
        "source": source_directory,
        "status": "created",
        "target": str(zip_path),
    }
    sprint(json.dumps(result, indent=4, sort_keys=True))
    return 0


def main():
    args = create_args_parser().parse_args()
    if args.scan:
        return scan(args.timeout)
    if not args.ipaddress:
        raise ExplainException("Give --ipaddress with --add-route, --config, --run, --backup or --restore")
    if args.config:
        return config(args.ipaddress, args.timeout)
    if args.run:
        return run(args.ipaddress, args.timeout)
    if args.backup:
        return backup(args.ipaddress, args.backup, args.timeout)
    if args.restore:
        return restore(args.ipaddress, args.restore, args.timeout)
    if len(args.add_route) not in (2, 3):
        raise ExplainException("--add-route expects NAME ADDRESS [AMS-NET-ID]")
    route_name, route_address = args.add_route[:2]
    ams_net_id = args.add_route[2] if len(args.add_route) == 3 else None
    route = AdsRoute.create(route_name, route_address, ams_net_id)
    password = args.password
    if password is None:
        password = getpass.getpass(f"Password for {args.username}@{args.ipaddress}: ")
    return add_route(args.ipaddress, route, args.username, password, args.timeout)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ExplainException as e:
        create_args_parser().print_help()
        eprint("\n\n" + e.message)
        sys.exit(1)
    except KeyboardInterrupt:
        eprint("\nads-admin_tool stopped.")
        sys.exit(0)
    except Exception:
        traceback.print_exc(file=sys.stdout)
    create_args_parser().print_help()
    sys.exit(2)
