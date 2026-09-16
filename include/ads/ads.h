#pragma once

#include <ads/AdsDef.h>

#include <cstdint>
#include <string>
#include <string_view>

namespace plc {
namespace beckhoff {

// source:
// https://infosys.beckhoff.com/english.php?content=../content/1033/tcplclib_tc2_utilities/35330059.html&id=
enum class AdsDataTypeId : std::uint32_t
{
    Void = 0,
    Int8 = 16,
    UInt8 = 17,
    Int16 = 2,
    UInt16 = 18,
    Int32 = 3,
    UInt32 = 19,
    Int64 = 20,
    UInt64 = 21,
    Real32 = 4,
    Real64 = 5,
    BigType = 65,
    String = 30,
    WString = 31,
    Real80 = 32,
    Bit = 33,
    MaxTypes = 34
};

std::string_view to_string(AdsDataTypeId type);

struct AdsError
{
    std::uint32_t hresult{}; // HRESULT, see https://learn.microsoft.com/en-us/windows/win32/seccrypto/common-hresult-values
    std::uint32_t adsErrorCode{}; // code as return by Ads function and in AdsException
    std::string description{};
};

std::string ads_error_as_string(std::uint32_t adsErrorCode);
std::string to_string(AmsNetId id);

} // namespace beckhoff
} // namespace plc

