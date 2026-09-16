#include "beckhoff/ads.h"

#include <format>
#include <string>
#include <vector>

namespace plc {
namespace beckhoff {

// Commented out lines in ADS_ERROR_VALUE are for identifiers and values that are already defined in AdsDef.h
// the table is derived from https://infosys.beckhoff.com/content/1033/tcplclib_tc3_ipcdiag/374277003.html?id=3226823192632100220

enum ADS_ERROR_VALUE
{
    ERR_NOERROR = 0x0,
    ERR_INTERNAL = 0x1,
    ERR_NORTIME = 0x2,
    ERR_ALLOCLOCKEDMEM = 0x3,
    ERR_INSERTMAILBOX = 0x4,
    ERR_WRONGRECEIVEHMSG = 0x5,
    ERR_TARGETPORTNOTFOUND = 0x6,
    ERR_TARGETMACHINENOTFOUND = 0x7,
    ERR_UNKNOWNCMDID = 0x8,
    ERR_BADTASKID = 0x9,
    ERR_NOIO = 0xA,
    ERR_UNKNOWNAMSCMD = 0xB,
    ERR_WIN32ERROR = 0xC,
    ERR_PORTNOTCONNECTED = 0xD,
    ERR_INVALIDAMSLENGTH = 0xE,
    ERR_INVALIDAMSNETID = 0xF,
    ERR_LOWINSTLEVEL = 0x10,
    ERR_NODEBUGINTAVAILABLE = 0x11,
    ERR_PORTDISABLED = 0x12,
    ERR_PORTALREADYCONNECTED = 0x13,
    ERR_AMSSYNC_W32ERROR = 0x14,
    ERR_AMSSYNC_TIMEOUT = 0x15,
    ERR_AMSSYNC_AMSERROR = 0x16,
    ERR_AMSSYNC_NOINDEXINMAP = 0x17,
    ERR_INVALIDAMSPORT = 0x18,
    ERR_NOMEMORY = 0x19,
    ERR_TCPSEND = 0x1A,
    ERR_HOSTUNREACHABLE = 0x1B,
    ERR_INVALIDAMSFRAGMENT = 0x1C,
    ERR_TLSSEND = 0x1D,
    ERR_ACCESSDENIED = 0x1E,
    ROUTERERR_NOLOCKEDMEMORY = 0x500,
    ROUTERERR_RESIZEMEMORY = 0x501,
    ROUTERERR_MAILBOXFULL = 0x502,
    ROUTERERR_DEBUGBOXFULL = 0x503,
    ROUTERERR_UNKNOWNPORTTYPE = 0x504,
    ROUTERERR_NOTINITIALIZED = 0x505,
    // ROUTERERR_PORTALREADYINUSE = 0x506,
    // ROUTERERR_NOTREGISTERED = 0x507,
    // ROUTERERR_NOMOREQUEUES = 0x508,
    ROUTERERR_INVALIDPORT = 0x509,
    ROUTERERR_NOTACTIVATED = 0x50A,
    ROUTERERR_FRAGMENTBOXFULL = 0x50B,
    ROUTERERR_FRAGMENTTIMEOUT = 0x50C,
    ROUTERERR_TOBEREMOVED = 0x50D,
    // ADSERR_DEVICE_ERROR = 0x700,
    // ADSERR_DEVICE_SRVNOTSUPP = 0x701,
    // ADSERR_DEVICE_INVALIDGRP = 0x702,
    // ADSERR_DEVICE_INVALIDOFFSET = 0x703,
    // ADSERR_DEVICE_INVALIDACCESS = 0x704,
    // ADSERR_DEVICE_INVALIDSIZE = 0x705,
    // ADSERR_DEVICE_INVALIDDATA = 0x706,
    // ADSERR_DEVICE_NOTREADY = 0x707,
    // ADSERR_DEVICE_BUSY = 0x708,
    // ADSERR_DEVICE_INVALIDCONTEXT = 0x709,
    // ADSERR_DEVICE_NOMEMORY = 0x70A,
    // ADSERR_DEVICE_INVALIDPARM = 0x70B,
    // ADSERR_DEVICE_NOTFOUND = 0x70C,
    // ADSERR_DEVICE_SYNTAX = 0x70D,
    // ADSERR_DEVICE_INCOMPATIBLE = 0x70E,
    // ADSERR_DEVICE_EXISTS = 0x70F,
    // ADSERR_DEVICE_SYMBOLNOTFOUND = 0x710,
    // ADSERR_DEVICE_SYMBOLVERSIONINVALID = 0x711,
    // ADSERR_DEVICE_INVALIDSTATE = 0x712,
    // ADSERR_DEVICE_TRANSMODENOTSUPP = 0x713,
    // ADSERR_DEVICE_NOTIFYHNDINVALID = 0x714,
    // ADSERR_DEVICE_CLIENTUNKNOWN = 0x715,
    // ADSERR_DEVICE_NOMOREHDLS = 0x716,
    // ADSERR_DEVICE_INVALIDWATCHSIZE = 0x717,
    // ADSERR_DEVICE_NOTINIT = 0x718,
    // ADSERR_DEVICE_TIMEOUT = 0x719,
    // ADSERR_DEVICE_NOINTERFACE = 0x71A,
    // ADSERR_DEVICE_INVALIDINTERFACE = 0x71B,
    // ADSERR_DEVICE_INVALIDCLSID = 0x71C,
    // ADSERR_DEVICE_INVALIDOBJID = 0x71D,
    // ADSERR_DEVICE_PENDING = 0x71E,
    // ADSERR_DEVICE_ABORTED = 0x71F,
    // ADSERR_DEVICE_WARNING = 0x720,
    // ADSERR_DEVICE_INVALIDARRAYIDX = 0x721,
    // ADSERR_DEVICE_SYMBOLNOTACTIVE = 0x722,
    // ADSERR_DEVICE_ACCESSDENIED = 0x723,
    // ADSERR_DEVICE_LICENSENOTFOUND = 0x724,
    // ADSERR_DEVICE_LICENSEEXPIRED = 0x725,
    // ADSERR_DEVICE_LICENSEEXCEEDED = 0x726,
    // ADSERR_DEVICE_LICENSEINVALID = 0x727,
    // ADSERR_DEVICE_LICENSESYSTEMID = 0x728,
    // ADSERR_DEVICE_LICENSENOTIMELIMIT = 0x729,
    // ADSERR_DEVICE_LICENSEFUTUREISSUE = 0x72A,
    // ADSERR_DEVICE_LICENSETIMETOLONG = 0x72B,
    // ADSERR_DEVICE_EXCEPTION = 0x72C,
    // ADSERR_DEVICE_LICENSEDUPLICATED = 0x72D,
    // ADSERR_DEVICE_SIGNATUREINVALID = 0x72E,
    // ADSERR_DEVICE_CERTIFICATEINVALID = 0x72F,
    ADSERR_DEVICE_LICENSEOEMNOTFOUND = 0x730,
    ADSERR_DEVICE_LICENSERESTRICTED = 0x731,
    ADSERR_DEVICE_LICENSEDEMODENIED = 0x732,
    ADSERR_DEVICE_INVALIDFNCID = 0x733,
    ADSERR_DEVICE_OUTOFRANGE = 0x734,
    ADSERR_DEVICE_INVALIDALIGNMENT = 0x735,
    ADSERR_DEVICE_LICENSEPLATFORM = 0x736,
    ADSERR_DEVICE_FORWARD_PL = 0x737,
    ADSERR_DEVICE_FORWARD_DL = 0x738,
    ADSERR_DEVICE_FORWARD_RT = 0x739,
    // ADSERR_CLIENT_ERROR = 0x740,
    // ADSERR_CLIENT_INVALIDPARM = 0x741,
    // ADSERR_CLIENT_LISTEMPTY = 0x742,
    // ADSERR_CLIENT_VARUSED = 0x743,
    // ADSERR_CLIENT_DUPLINVOKEID = 0x744,
    // ADSERR_CLIENT_SYNCTIMEOUT = 0x745,
    // ADSERR_CLIENT_W32ERROR = 0x746,
    // ADSERR_CLIENT_TIMEOUTINVALID = 0x747,
    // ADSERR_CLIENT_PORTNOTOPEN = 0x748,
    // ADSERR_CLIENT_NOAMSADDR = 0x749,
    // ADSERR_CLIENT_SYNCINTERNAL = 0x750,
    // ADSERR_CLIENT_ADDHASH = 0x751,
    // ADSERR_CLIENT_REMOVEHASH = 0x752,
    // ADSERR_CLIENT_NOMORESYM = 0x753,
    // ADSERR_CLIENT_SYNCRESINVALID = 0x754,
    // ADSERR_CLIENT_SYNCPORTLOCKED = 0x755,
    ADSERR_CLIENT_REQUESTCANCELLED = 0x756,
    RTERR_INTERNAL = 0x1000,
    RTERR_BADTIMERPERIODS = 0x1001,
    RTERR_INVALIDTASKPTR = 0x1002,
    RTERR_INVALIDSTACKPTR = 0x1003,
    RTERR_PRIOEXISTS = 0x1004,
    RTERR_NOMORETCB = 0x1005,
    RTERR_NOMORESEMAS = 0x1006,
    RTERR_NOMOREQUEUES = 0x1007,
    RTERR_EXTIRQALREADYDEF = 0x100D,
    RTERR_EXTIRQNOTDEF = 0x100E,
    RTERR_EXTIRQINSTALLFAILED = 0x100F,
    RTERR_VMXNOTSUPPORTED = 0x1010,
    RTERR_IRQLNOTLESSOREQUAL = 0x1017,
    RTERR_VMXDISABLED = 0x1018,
    RTERR_VMXCONTROLSMISSING = 0x1019,
    RTERR_VMXENABLEFAILS = 0x101A
};

static std::vector<AdsError> adsErrors = {
    {0x98110000, ERR_NOERROR, "No error."},
    {0x98110001, ERR_INTERNAL, "Internal error."},
    {0x98110002, ERR_NORTIME, "No real time."},
    {0x98110003, ERR_ALLOCLOCKEDMEM, "Allocation locked - memory error."},
    {0x98110004, ERR_INSERTMAILBOX, "Mailbox full - the ADS message could not be sent. Reducing the number of ADS messages per cycle will help."},
    {0x98110005, ERR_WRONGRECEIVEHMSG, "Wrong HMSG."},
    {0x98110006, ERR_TARGETPORTNOTFOUND, "Target port not found - ADS server is not started, not reachable or not installed."},
    {0x98110007, ERR_TARGETMACHINENOTFOUND, "Target computer not found - AMS route was not found."},
    {0x98110008, ERR_UNKNOWNCMDID, "Unknown command ID."},
    {0x98110009, ERR_BADTASKID, "Invalid task ID."},
    {0x9811000A, ERR_NOIO, "No IO."},
    {0x9811000B, ERR_UNKNOWNAMSCMD, "Unknown AMS command."},
    {0x9811000C, ERR_WIN32ERROR, "Win32 error."},
    {0x9811000D, ERR_PORTNOTCONNECTED, "Port not connected."},
    {0x9811000E, ERR_INVALIDAMSLENGTH, "Invalid AMS length."},
    {0x9811000F, ERR_INVALIDAMSNETID, "Invalid AMS Net ID."},
    {0x98110010, ERR_LOWINSTLEVEL, "Installation level is too low -TwinCAT 2 license error."},
    {0x98110011, ERR_NODEBUGINTAVAILABLE, "No debugging available."},
    {0x98110012, ERR_PORTDISABLED, "Port disabled - TwinCAT system service not started."},
    {0x98110013, ERR_PORTALREADYCONNECTED, "Port already connected."},
    {0x98110014, ERR_AMSSYNC_W32ERROR, "AMS Sync Win32 error."},
    {0x98110015, ERR_AMSSYNC_TIMEOUT, "AMS Sync Timeout."},
    {0x98110016, ERR_AMSSYNC_AMSERROR, "AMS Sync error."},
    {0x98110017, ERR_AMSSYNC_NOINDEXINMAP, "No index map for AMS Sync available."},
    {0x98110018, ERR_INVALIDAMSPORT, "Invalid AMS port."},
    {0x98110019, ERR_NOMEMORY, "No memory."},
    {0x9811001A, ERR_TCPSEND, "TCP send error."},
    {0x9811001B, ERR_HOSTUNREACHABLE, "Host unreachable."},
    {0x9811001C, ERR_INVALIDAMSFRAGMENT, "Invalid AMS fragment."},
    {0x9811001D, ERR_TLSSEND, "TLS send error - secure ADS connection failed."},
    {0x9811001E, ERR_ACCESSDENIED, "Access denied - secure ADS access denied."},
    {0x98110500, ROUTERERR_NOLOCKEDMEMORY, "Locked memory cannot be allocated."},
    {0x98110501, ROUTERERR_RESIZEMEMORY, "The router memory size could not be changed."},
    {0x98110502, ROUTERERR_MAILBOXFULL, "The mailbox has reached the maximum number of possible messages."},
    {0x98110503, ROUTERERR_DEBUGBOXFULL, "The Debug mailbox has reached the maximum number of possible messages."},
    {0x98110504, ROUTERERR_UNKNOWNPORTTYPE, "The port type is unknown."},
    {0x98110505, ROUTERERR_NOTINITIALIZED, "The router is not initialized."},
    {0x98110506, ROUTERERR_PORTALREADYINUSE, "The port number is already assigned."},
    {0x98110507, ROUTERERR_NOTREGISTERED, "The port is not registered."},
    {0x98110508, ROUTERERR_NOMOREQUEUES, "The maximum number of ports has been reached."},
    {0x98110509, ROUTERERR_INVALIDPORT, "The port is invalid."},
    {0x9811050A, ROUTERERR_NOTACTIVATED, "The router is not active."},
    {0x9811050B, ROUTERERR_FRAGMENTBOXFULL, "The mailbox has reached the maximum number for fragmented messages."},
    {0x9811050C, ROUTERERR_FRAGMENTTIMEOUT, "A fragment timeout has occurred."},
    {0x9811050D, ROUTERERR_TOBEREMOVED, "The port is removed."},
    {0x98110700, ADSERR_DEVICE_ERROR, "General device error."},
    {0x98110701, ADSERR_DEVICE_SRVNOTSUPP, "Service is not supported by the server."},
    {0x98110702, ADSERR_DEVICE_INVALIDGRP, "Invalid index group."},
    {0x98110703, ADSERR_DEVICE_INVALIDOFFSET, "Invalid index offset."},
    {0x98110704, ADSERR_DEVICE_INVALIDACCESS, "Reading or writing not permitted. Several causes are possible. For example, an incorrect password was entered when creating routes."},
    {0x98110705, ADSERR_DEVICE_INVALIDSIZE, "Parameter size not correct."},
    {0x98110706, ADSERR_DEVICE_INVALIDDATA, "Invalid data values."},
    {0x98110707, ADSERR_DEVICE_NOTREADY, "Device is not ready to operate."},
    {0x98110708, ADSERR_DEVICE_BUSY, "Device is busy."},
    {0x98110709, ADSERR_DEVICE_INVALIDCONTEXT, "Invalid operating system context. This can result from use of ADS blocks in different tasks. It may be possible to resolve this through multitasking synchronization in the PLC."},
    {0x9811070A, ADSERR_DEVICE_NOMEMORY, "Insufficient memory."},
    {0x9811070B, ADSERR_DEVICE_INVALIDPARM, "Invalid parameter values."},
    {0x9811070C, ADSERR_DEVICE_NOTFOUND, "Not found (files, ...)."},
    {0x9811070D, ADSERR_DEVICE_SYNTAX, "Syntax error in file or command."},
    {0x9811070E, ADSERR_DEVICE_INCOMPATIBLE, "Objects do not match."},
    {0x9811070F, ADSERR_DEVICE_EXISTS, "Object already exists."},
    {0x98110710, ADSERR_DEVICE_SYMBOLNOTFOUND, "Symbol not found."},
    {0x98110711, ADSERR_DEVICE_SYMBOLVERSIONINVALID, "Invalid symbol version. This can occur due to an online change. Create a new handle."},
    {0x98110712, ADSERR_DEVICE_INVALIDSTATE, "Device (server) is in invalid state."},
    {0x98110713, ADSERR_DEVICE_TRANSMODENOTSUPP, "AdsTransMode not supported."},
    {0x98110714, ADSERR_DEVICE_NOTIFYHNDINVALID, "Notification handle is invalid."},
    {0x98110715, ADSERR_DEVICE_CLIENTUNKNOWN, "Notification client not registered."},
    {0x98110716, ADSERR_DEVICE_NOMOREHDLS, "No further handle available."},
    {0x98110717, ADSERR_DEVICE_INVALIDWATCHSIZE, "Notification size too large."},
    {0x98110718, ADSERR_DEVICE_NOTINIT, "Device not initialized."},
    {0x98110719, ADSERR_DEVICE_TIMEOUT, "Device has a timeout."},
    {0x9811071A, ADSERR_DEVICE_NOINTERFACE, "Interface query failed."},
    {0x9811071B, ADSERR_DEVICE_INVALIDINTERFACE, "Wrong interface requested."},
    {0x9811071C, ADSERR_DEVICE_INVALIDCLSID, "Class ID is invalid."},
    {0x9811071D, ADSERR_DEVICE_INVALIDOBJID, "Object ID is invalid."},
    {0x9811071E, ADSERR_DEVICE_PENDING, "Request pending."},
    {0x9811071F, ADSERR_DEVICE_ABORTED, "Request is aborted."},
    {0x98110720, ADSERR_DEVICE_WARNING, "Signal warning."},
    {0x98110721, ADSERR_DEVICE_INVALIDARRAYIDX, "Invalid array index."},
    {0x98110722, ADSERR_DEVICE_SYMBOLNOTACTIVE, "Symbol not active."},
    {0x98110723, ADSERR_DEVICE_ACCESSDENIED, "Access denied. Several causes are possible. For example, a unidirectional ADS route is used in the opposite direction."},
    {0x98110724, ADSERR_DEVICE_LICENSENOTFOUND, "Missing license."},
    {0x98110725, ADSERR_DEVICE_LICENSEEXPIRED, "License expired."},
    {0x98110726, ADSERR_DEVICE_LICENSEEXCEEDED, "License exceeded."},
    {0x98110727, ADSERR_DEVICE_LICENSEINVALID, "Invalid license."},
    {0x98110728, ADSERR_DEVICE_LICENSESYSTEMID, "License problem: System ID is invalid."},
    {0x98110729, ADSERR_DEVICE_LICENSENOTIMELIMIT, "License not limited in time."},
    {0x9811072A, ADSERR_DEVICE_LICENSEFUTUREISSUE, "Licensing problem: time in the future."},
    {0x9811072B, ADSERR_DEVICE_LICENSETIMETOLONG, "License period too long."},
    {0x9811072C, ADSERR_DEVICE_EXCEPTION, "Exception at system startup."},
    {0x9811072D, ADSERR_DEVICE_LICENSEDUPLICATED, "License file read twice."},
    {0x9811072E, ADSERR_DEVICE_SIGNATUREINVALID, "Invalid signature."},
    {0x9811072F, ADSERR_DEVICE_CERTIFICATEINVALID, "Invalid certificate."},
    {0x98110730, ADSERR_DEVICE_LICENSEOEMNOTFOUND, "Public key not known from OEM."},
    {0x98110731, ADSERR_DEVICE_LICENSERESTRICTED, "License not valid for this system ID."},
    {0x98110732, ADSERR_DEVICE_LICENSEDEMODENIED, "Demo license prohibited."},
    {0x98110733, ADSERR_DEVICE_INVALIDFNCID, "Invalid function ID."},
    {0x98110734, ADSERR_DEVICE_OUTOFRANGE, "Outside the valid range."},
    {0x98110735, ADSERR_DEVICE_INVALIDALIGNMENT, "Invalid alignment."},
    {0x98110736, ADSERR_DEVICE_LICENSEPLATFORM, "Invalid platform level."},
    {0x98110737, ADSERR_DEVICE_FORWARD_PL, "Context - forward to passive level."},
    {0x98110738, ADSERR_DEVICE_FORWARD_DL, "Context - forward to dispatch level."},
    {0x98110739, ADSERR_DEVICE_FORWARD_RT, "Context - forward to real-time."},
    {0x98110740, ADSERR_CLIENT_ERROR, "Client error."},
    {0x98110741, ADSERR_CLIENT_INVALIDPARM, "Service contains an invalid parameter."},
    {0x98110742, ADSERR_CLIENT_LISTEMPTY, "Polling list is empty."},
    {0x98110743, ADSERR_CLIENT_VARUSED, "Var connection already in use."},
    {0x98110744, ADSERR_CLIENT_DUPLINVOKEID, "The called ID is already in use."},
    {0x98110745, ADSERR_CLIENT_SYNCTIMEOUT, "Timeout has occurred - the remote terminal is not responding in the specified ADS timeout. The route setting of the remote terminal may be configured incorrectly."},
    {0x98110746, ADSERR_CLIENT_W32ERROR, "Error in Win32 subsystem."},
    {0x98110747, ADSERR_CLIENT_TIMEOUTINVALID, "Invalid client timeout value."},
    {0x98110748, ADSERR_CLIENT_PORTNOTOPEN, "Port not open."},
    {0x98110749, ADSERR_CLIENT_NOAMSADDR, "No AMS address."},
    {0x98110750, ADSERR_CLIENT_SYNCINTERNAL, "Internal error in Ads sync."},
    {0x98110751, ADSERR_CLIENT_ADDHASH, "Hash table overflow."},
    {0x98110752, ADSERR_CLIENT_REMOVEHASH, "Key not found in the table."},
    {0x98110753, ADSERR_CLIENT_NOMORESYM, "No symbols in the cache."},
    {0x98110754, ADSERR_CLIENT_SYNCRESINVALID, "Invalid response received."},
    {0x98110755, ADSERR_CLIENT_SYNCPORTLOCKED, "Sync Port is locked."},
    {0x98110756, ADSERR_CLIENT_REQUESTCANCELLED, "The request was canceled."},
    {0x98111000, RTERR_INTERNAL, "Internal error in the real-time system."},
    {0x98111001, RTERR_BADTIMERPERIODS, "Timer value is not valid."},
    {0x98111002, RTERR_INVALIDTASKPTR, "Task pointer has the invalid value 0 (zero)."},
    {0x98111003, RTERR_INVALIDSTACKPTR, "Stack pointer has the invalid value 0 (zero)."},
    {0x98111004, RTERR_PRIOEXISTS, "The request task priority is already assigned."},
    {0x98111005, RTERR_NOMORETCB, "No free TCB (Task Control Block) available. The maximum number of TCBs is 64."},
    {0x98111006, RTERR_NOMORESEMAS, "No free semaphores available. The maximum number of semaphores is 64."},
    {0x98111007, RTERR_NOMOREQUEUES, "No free space available in the queue. The maximum number of positions in the queue is 64."},
    {0x9811100D, RTERR_EXTIRQALREADYDEF, "An external synchronization interrupt is already applied."},
    {0x9811100E, RTERR_EXTIRQNOTDEF, "No external sync interrupt applied."},
    {0x9811100F, RTERR_EXTIRQINSTALLFAILED, "Application of the external synchronization interrupt has failed."},
    {0x98111010, RTERR_IRQLNOTLESSOREQUAL, "Call of a service function in the wrong context"},
    {0x98111017, RTERR_VMXNOTSUPPORTED, "Intel VT-x extension is not supported."},
    {0x98111018, RTERR_VMXDISABLED, "Intel VT-x extension is not enabled in the BIOS."},
    {0x98111019, RTERR_VMXCONTROLSMISSING, "Missing function in Intel VT-x extension."},
    {0x9811101A, RTERR_VMXENABLEFAILS, "Activation of Intel VT-x fails."}};

std::string ads_error_as_string(std::uint32_t adsErrorCode)
{
    auto it = std::ranges::find_if(adsErrors, [adsErrorCode](const AdsError & err) {
        return err.adsErrorCode == adsErrorCode;
    });

    if (it != adsErrors.end())
    {
        return it->description;
    }
    return {};
}

std::string to_string(AmsNetId id)
{
    return std::format("{}.{}.{}.{}.{}.{}", id.b[0], id.b[1], id.b[2], id.b[3], id.b[4], id.b[5]);
}

std::string_view to_string(AdsDataTypeId type)
{
    switch (type)
    {
    case AdsDataTypeId::Void: return "VOID";
    case AdsDataTypeId::Int8: return "INT8";
    case AdsDataTypeId::UInt8: return "UINT8";
    case AdsDataTypeId::Int16: return "INT16";
    case AdsDataTypeId::UInt16: return "UINT16";
    case AdsDataTypeId::Int32: return "INT32";
    case AdsDataTypeId::UInt32: return "UINT32";
    case AdsDataTypeId::Int64: return "INT64";
    case AdsDataTypeId::UInt64: return "UINT64";
    case AdsDataTypeId::Real32: return "REAL32";
    case AdsDataTypeId::Real64: return "REAL64";
    case AdsDataTypeId::BigType: return "BIGTYPE";
    case AdsDataTypeId::String: return "STRING";
    case AdsDataTypeId::WString: return "WSTRING";
    case AdsDataTypeId::Real80: return "REAL80";
    case AdsDataTypeId::Bit: return "BIT";
    case AdsDataTypeId::MaxTypes: return "MAXTYPES";
    }

    return "UNKNOWN";
}


} // namespace beckhoff
} // namespace plc

