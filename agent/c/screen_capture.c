#include "screen_capture.h"
#include <stdlib.h>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>

/* Captura tela principal e codifica como JPEG usando GDI + libjpeg (se disponível).
 * Sem libjpeg: retorna 0 frames (build sem ENABLE_JPEG). */
int hiprod_capture_screen_frames(hiprod_frame_t **frames, int *count) {
    *frames = NULL;
    *count = 0;

    HDC hScreen = GetDC(NULL);
    HDC hMemDC = CreateCompatibleDC(hScreen);
    if (!hScreen || !hMemDC) {
        if (hScreen) ReleaseDC(NULL, hScreen);
        return -1;
    }

    int w = GetSystemMetrics(SM_CXSCREEN);
    int h = GetSystemMetrics(SM_CYSCREEN);
    if (w <= 0 || h <= 0) {
        ReleaseDC(NULL, hScreen);
        DeleteDC(hMemDC);
        return -1;
    }

    HBITMAP hBmp = CreateCompatibleBitmap(hScreen, w, h);
    if (!hBmp) {
        ReleaseDC(NULL, hScreen);
        DeleteDC(hMemDC);
        return -1;
    }
    SelectObject(hMemDC, hBmp);
    BitBlt(hMemDC, 0, 0, w, h, hScreen, 0, 0, SRCCOPY);

    BITMAPINFOHEADER bi = { 0 };
    bi.biSize = sizeof(bi);
    bi.biWidth = w;
    bi.biHeight = -h; /* top-down */
    bi.biPlanes = 1;
    bi.biBitCount = 24;
    bi.biCompression = BI_RGB;

    size_t row_bytes = ((size_t)w * 3 + 3) & ~3;
    size_t image_size = row_bytes * (size_t)h;
    unsigned char *rgb = (unsigned char *)malloc(image_size);
    if (!rgb) {
        DeleteObject(hBmp);
        DeleteDC(hMemDC);
        ReleaseDC(NULL, hScreen);
        return -1;
    }

    GetDIBits(hMemDC, hBmp, 0, (UINT)h, rgb, (BITMAPINFO *)&bi, DIB_RGB_COLORS);

    DeleteObject(hBmp);
    DeleteDC(hMemDC);
    ReleaseDC(NULL, hScreen);

#ifdef ENABLE_JPEG_ENCODE
    /* Codificar RGB para JPEG (requer libjpeg) */
    extern int hiprod_rgb_to_jpeg(const unsigned char *rgb, int width, int height,
                                  unsigned char **out_data, size_t *out_len);
    unsigned char *jpeg_data = NULL;
    size_t jpeg_len = 0;
    int r = hiprod_rgb_to_jpeg(rgb, w, h, &jpeg_data, &jpeg_len);
    free(rgb);
    if (r != 0 || !jpeg_data) return -1;

    *frames = (hiprod_frame_t *)malloc(sizeof(hiprod_frame_t));
    if (!*frames) { free(jpeg_data); return -1; }
    (*frames)[0].data = jpeg_data;
    (*frames)[0].len = jpeg_len;
    *count = 1;
    return 0;
#else
    (void)row_bytes;
    (void)image_size;
    free(rgb);
    /* Sem encoder JPEG: não enviamos frames */
    return 0;
#endif
}

void hiprod_frames_free(hiprod_frame_t *frames, int count) {
    if (!frames) return;
    for (int i = 0; i < count; i++)
        free(frames[i].data);
    free(frames);
}

#else
/* Não-Windows: sem captura */
int hiprod_capture_screen_frames(hiprod_frame_t **frames, int *count) {
    (void)frames;
    *count = 0;
    return 0;
}
void hiprod_frames_free(hiprod_frame_t *frames, int count) {
    (void)frames;
    (void)count;
}
#endif
