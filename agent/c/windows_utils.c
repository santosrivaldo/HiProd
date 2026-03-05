#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

void win_get_foreground_window_title(char *buf, int max_len) {
    buf[0] = '\0';
    HWND h = GetForegroundWindow();
    if (!h) return;
    GetWindowTextA(h, buf, max_len);
    if (!buf[0]) strncpy(buf, "Sistema Local", max_len - 1);
}

unsigned int win_get_idle_seconds(void) {
    LASTINPUTINFO li = { sizeof(li) };
    if (!GetLastInputInfo(&li)) return 0;
    DWORD now = GetTickCount();
    DWORD elapsed = (now - li.dwTime) / 1000;
    return (unsigned int)elapsed;
}
#else
#include "windows_utils.h"
#include <string.h>

void win_get_foreground_window_title(char *buf, int max_len) {
    (void)max_len;
    strncpy(buf, "Sistema Local", max_len - 1);
    buf[max_len - 1] = '\0';
}

unsigned int win_get_idle_seconds(void) {
    return 0;
}
#endif
