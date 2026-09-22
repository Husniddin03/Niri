#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <linux/input-event-codes.h>
#include <wayland-client.h>
#include "wlr-virtual-pointer-unstable-v1-client-protocol.h"

static struct wl_seat *seat = NULL;
static struct zwlr_virtual_pointer_manager_v1 *vp_mgr = NULL;

static void registry_handle_global(void *data, struct wl_registry *reg, uint32_t name, const char *interface, uint32_t version) {
    if (strcmp(interface, "wl_seat") == 0) {
        seat = wl_registry_bind(reg, name, &wl_seat_interface, version < 7 ? version : 7);
    } else if (strcmp(interface, "zwlr_virtual_pointer_manager_v1") == 0) {
        vp_mgr = wl_registry_bind(reg, name, &zwlr_virtual_pointer_manager_v1_interface, 1);
    }
}
static void registry_handle_remove(void *data, struct wl_registry *reg, uint32_t name) {}

static const struct wl_registry_listener reg_listener = {
    .global = registry_handle_global,
    .global_remove = registry_handle_remove,
};

static uint32_t get_time_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint32_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

int main(int argc, char *argv[]) {
    struct wl_display *dpy = wl_display_connect(NULL);
    if (!dpy) {
        fprintf(stderr, "Failed to connect to Wayland display\n");
        return 1;
    }

    struct wl_registry *reg = wl_display_get_registry(dpy);
    wl_registry_add_listener(reg, &reg_listener, NULL);
    wl_display_roundtrip(dpy);

    if (!seat || !vp_mgr) {
        fprintf(stderr, "Missing wl_seat or zwlr_virtual_pointer_manager_v1\n");
        wl_display_disconnect(dpy);
        return 1;
    }

    struct zwlr_virtual_pointer_v1 *vp = zwlr_virtual_pointer_manager_v1_create_virtual_pointer(vp_mgr, seat);
    if (!vp) {
        fprintf(stderr, "Failed to create virtual pointer\n");
        wl_display_disconnect(dpy);
        return 1;
    }
    wl_display_flush(dpy);

    // Unbuffer stdin & stdout
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("READY\n");

    char line[256];
    while (fgets(line, sizeof(line), stdin)) {
        char cmd = line[0];
        if (cmd == 'm') {
            // Move: m <dx> <dy>
            double dx = 0.0, dy = 0.0;
            if (sscanf(line + 1, "%lf %lf", &dx, &dy) == 2) {
                uint32_t t = get_time_ms();
                zwlr_virtual_pointer_v1_motion(vp, t, wl_fixed_from_double(dx), wl_fixed_from_double(dy));
                zwlr_virtual_pointer_v1_frame(vp);
                wl_display_flush(dpy);
            }
        } else if (cmd == 'd') {
            // Button Down: d left | d right
            char btn_name[32] = {0};
            sscanf(line + 1, "%31s", btn_name);
            uint32_t btn = BTN_LEFT;
            if (strcasecmp(btn_name, "right") == 0) btn = BTN_RIGHT;
            else if (strcasecmp(btn_name, "middle") == 0) btn = BTN_MIDDLE;

            uint32_t t = get_time_ms();
            zwlr_virtual_pointer_v1_button(vp, t, btn, WL_POINTER_BUTTON_STATE_PRESSED);
            zwlr_virtual_pointer_v1_frame(vp);
            wl_display_flush(dpy);
        } else if (cmd == 'u') {
            // Button Up: u left | u right
            char btn_name[32] = {0};
            sscanf(line + 1, "%31s", btn_name);
            uint32_t btn = BTN_LEFT;
            if (strcasecmp(btn_name, "right") == 0) btn = BTN_RIGHT;
            else if (strcasecmp(btn_name, "middle") == 0) btn = BTN_MIDDLE;

            uint32_t t = get_time_ms();
            zwlr_virtual_pointer_v1_button(vp, t, btn, WL_POINTER_BUTTON_STATE_RELEASED);
            zwlr_virtual_pointer_v1_frame(vp);
            wl_display_flush(dpy);
        } else if (cmd == 'c') {
            // Click: c left | c right
            char btn_name[32] = {0};
            sscanf(line + 1, "%31s", btn_name);
            uint32_t btn = BTN_LEFT;
            if (strcasecmp(btn_name, "right") == 0) btn = BTN_RIGHT;
            else if (strcasecmp(btn_name, "middle") == 0) btn = BTN_MIDDLE;

            uint32_t t = get_time_ms();
            zwlr_virtual_pointer_v1_button(vp, t, btn, WL_POINTER_BUTTON_STATE_PRESSED);
            zwlr_virtual_pointer_v1_frame(vp);
            wl_display_flush(dpy);
            usleep(15000); // 15ms
            t = get_time_ms();
            zwlr_virtual_pointer_v1_button(vp, t, btn, WL_POINTER_BUTTON_STATE_RELEASED);
            zwlr_virtual_pointer_v1_frame(vp);
            wl_display_flush(dpy);
        } else if (cmd == 's') {
            // Scroll: s <dy>
            double dy = 0.0;
            if (sscanf(line + 1, "%lf", &dy) == 1) {
                uint32_t t = get_time_ms();
                zwlr_virtual_pointer_v1_axis_discrete(vp, t, 0, wl_fixed_from_double(dy * 15.0), (int32_t)dy);
                zwlr_virtual_pointer_v1_frame(vp);
                wl_display_flush(dpy);
            }
        } else if (cmd == 'a') {
            // Absolute Move: a <x> <y> <x_extent> <y_extent>
            uint32_t x = 0, y = 0, x_ext = 1920, y_ext = 1080;
            int n = sscanf(line + 1, "%u %u %u %u", &x, &y, &x_ext, &y_ext);
            if (n >= 2) {
                uint32_t t = get_time_ms();
                zwlr_virtual_pointer_v1_motion_absolute(vp, t, x, y, x_ext, y_ext);
                zwlr_virtual_pointer_v1_frame(vp);
                wl_display_flush(dpy);
            }
        } else if (cmd == 'q') {
            break;
        }
    }

    zwlr_virtual_pointer_v1_destroy(vp);
    wl_display_disconnect(dpy);
    return 0;
}
