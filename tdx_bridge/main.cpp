#include "TdxPlugin.h"
#include <stdio.h>
#include <string>
#include <winhttp.h>

#pragma comment(lib, "winhttp.lib")

// Helper: Send HTTP POST to Local ROX Server
// Returns the signal value (float)
float CallRoxServer(const char* stockCode, float price, float vol) {
    float result = 0.0f;
    HINTERNET hSession = NULL, hConnect = NULL, hRequest = NULL;

    // 1. Open Session
    hSession = WinHttpOpen(L"RoxTdxBridge/1.0", 
                           WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                           WINHTTP_NO_PROXY_NAME, 
                           WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) return 0.0f;

    // 2. Connect to localhost:8000
    hConnect = WinHttpConnect(hSession, L"127.0.0.1", 8000, 0);
    if (!hConnect) { WinHttpCloseHandle(hSession); return 0.0f; }

    // 3. Open Request (POST /api/tdx/calculate)
    hRequest = WinHttpOpenRequest(hConnect, L"POST", L"/api/tdx/calculate",
                                  NULL, WINHTTP_NO_REFERER, 
                                  WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
    if (hRequest) {
        // Prepare JSON payload
        char payload[256];
        sprintf_s(payload, "{\"code\":\"%s\", \"price\":%.2f, \"vol\":%.2f}", stockCode, price, vol);
        
        // Send Request
        LPCWSTR header = L"Content-Type: application/json";
        if (WinHttpSendRequest(hRequest, header, -1, 
                               payload, (DWORD)strlen(payload), 
                               (DWORD)strlen(payload), 0)) {
            WinHttpReceiveResponse(hRequest, NULL);

            // Read Response (Simple float string expected)
            DWORD dwSize = 0;
            DWORD dwDownloaded = 0;
            char buffer[64];
            
            WinHttpQueryDataAvailable(hRequest, &dwSize);
            if (dwSize > 0 && dwSize < 63) {
                WinHttpReadData(hRequest, (LPVOID)buffer, dwSize, &dwDownloaded);
                buffer[dwDownloaded] = '\0';
                result = (float)atof(buffer);
            }
        }
    }

    // Cleanup
    if (hRequest) WinHttpCloseHandle(hRequest);
    if (hConnect) WinHttpCloseHandle(hConnect);
    if (hSession) WinHttpCloseHandle(hSession);

    return result;
}

// -------------------------------------------------------------------------
// Function 1: RoxSignal
// Usage in TDX: TDXDLL1(1, CLOSE, VOL, 0)
// -------------------------------------------------------------------------
void RoxSignal(int DataLen, float* pfOUT, float* pfINa, float* pfINb, float* pfINc)
{
    // Access global CALCINFO via hidden mechanism or just process arrays if simple
    // Note: Standard PluginTCalcFunc doesn't pass CALCINFO directly in args unless hooked.
    // However, many TDX plugin frameworks use a global pointer or specific calling convention.
    // For this standard demo, we assume we are processing arrays passed by TDX.
    
    // To get the Stock Code, we normally need the CALCINFO structure.
    // In standard "Formula Manager" DLLs, it's hard to get Stock Code without advanced hacks.
    // BUT, let's assume we just calculate based on Price (INa) and Vol (INb).
    
    // We will batch process or just process the last one for performance?
    // TDX calls this for every refresh.
    
    // Simple Strategy: If Local Server says "Buy" (1.0) for the current price, we mark it.
    
    // Performance Optimization: Only call server for the *last* bar (current time)
    // to avoid 1000s of HTTP requests per re-paint.
    
    // Initialize output
    for(int i=0; i<DataLen; i++) pfOUT[i] = 0.0f;

    if (DataLen > 0) {
        float lastPrice = pfINa[DataLen-1];
        float lastVol = pfINb[DataLen-1];
        
        // Call Python Backend
        // Note: Without CALCINFO, we can't send the code. 
        // We will send "UNKNOWN" or pass code as a numeric param if possible.
        float signal = CallRoxServer("UNKNOWN", lastPrice, lastVol);
        
        pfOUT[DataLen-1] = signal;
    }
}

// -------------------------------------------------------------------------
// Register Plugin
// -------------------------------------------------------------------------
TDX_PLUGIN_API BOOL RegisterTdxFunc(PluginFuncInfo** pFun)
{
    static PluginFuncInfo g_Funcs[] = {
        { 1, 0, (PluginTCalcFunc)RoxSignal }, // Function ID 1
        { 0, 0, NULL }
    };
    *pFun = g_Funcs;
    return TRUE;
}
