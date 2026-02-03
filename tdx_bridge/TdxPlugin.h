#ifndef __TDX_PLUGIN_H__
#define __TDX_PLUGIN_H__

#include <windows.h>

// Data structure for stock information (Bar data)
typedef struct _STKDATA
{
    DWORD   m_dwTime;       // Time (YYYYMMDD or YYYYMMDDHHMM)
    float   m_fOpen;        // Open
    float   m_fHigh;        // High
    float   m_fLow;         // Low
    float   m_fClose;       // Close
    float   m_fAmount;      // Amount
    float   m_fVol;         // Volume
    float   m_fAmount2;     // Open Interest or Reserved
} STKDATA;

// Calculation Information structure passed by TDX
typedef struct _CALCINFO
{
    const DWORD           m_dwSize;       // Structure size
    const DWORD           m_dwVersion;    // TDX Version
    const DWORD           m_dwSerial;     // Serial number
    const char*           m_strStkLabel;  // Stock Code (e.g., "600519")
    const BOOL            m_bIndex;       // Is Index?
    const int             m_nNumData;     // Number of data points
    const STKDATA*        m_pData;        // Pointer to data array
} CALCINFO;

// Function pointer type for TDX formula functions
typedef void(*PluginTCalcFunc)(int DataLen, float* pfOUT, float* pfINa, float* pfINb, float* pfINc);

// Plugin Function Info structure
typedef struct _PluginFuncInfo
{
    unsigned short  nFuncMark;      // Function ID (1-based)
    unsigned short  nCallType;      // Call type (0)
    PluginTCalcFunc pCallFunc;      // Function pointer
} PluginFuncInfo;

// Export macro
#define TDX_PLUGIN_API extern "C" __declspec(dllexport)

#endif // __TDX_PLUGIN_H__
