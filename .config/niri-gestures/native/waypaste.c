#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mman.h>
#include <wayland-client.h>
#include "virtual-keyboard-unstable-v1-client-protocol.h"
#include <xkbcommon/xkbcommon.h>

static struct wl_seat *seat = NULL;
static struct zwp_virtual_keyboard_manager_v1 *vk_mgr = NULL;

static void registry_handle_global(void *data, struct wl_registry *reg, uint32_t name, const char *interface, uint32_t version) {
    if (strcmp(interface, "wl_seat") == 0) {
        seat = wl_registry_bind(reg, name, &wl_seat_interface, version < 7 ? version : 7);
    } else if (strcmp(interface, "zwp_virtual_keyboard_manager_v1") == 0) {
        vk_mgr = wl_registry_bind(reg, name, &zwp_virtual_keyboard_manager_v1_interface, 1);
    }
}
static void registry_handle_remove(void *data, struct wl_registry *reg, uint32_t name) {}

static const struct wl_registry_listener reg_listener = {
    .global = registry_handle_global,
    .global_remove = registry_handle_remove,
};

int main(int argc, char *argv[]) {
    // 120ms delay to allow previous window / input field to fully regain Wayland keyboard focus
    usleep(120000);

    struct wl_display *dpy = wl_display_connect(NULL);
    if (!dpy) return 1;
    struct wl_registry *reg = wl_display_get_registry(dpy);
    wl_registry_add_listener(reg, &reg_listener, NULL);
    wl_display_roundtrip(dpy);
    if (!seat || !vk_mgr) {
        wl_display_disconnect(dpy);
        return 1;
    }

    struct zwp_virtual_keyboard_v1 *vk = zwp_virtual_keyboard_manager_v1_create_virtual_keyboard(vk_mgr, seat);
    if (!vk) {
        wl_display_disconnect(dpy);
        return 1;
    }

    struct xkb_context *ctx = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    struct xkb_rule_names names = { .rules = "", .model = "", .layout = "us", .variant = "", .options = "" };
    struct xkb_keymap *keymap = xkb_keymap_new_from_names(ctx, &names, XKB_KEYMAP_COMPILE_NO_FLAGS);
    char *keymap_str = xkb_keymap_get_as_string(keymap, XKB_KEYMAP_FORMAT_TEXT_V1);
    size_t keymap_len = strlen(keymap_str);

    int fd = memfd_create("keymap", MFD_CLOEXEC);
    if (fd < 0) return 1;
    if (write(fd, keymap_str, keymap_len) != (ssize_t)keymap_len) {
        close(fd);
        return 1;
    }
    lseek(fd, 0, SEEK_SET);

    zwp_virtual_keyboard_v1_keymap(vk, WL_KEYBOARD_KEYMAP_FORMAT_XKB_V1, fd, keymap_len);
    wl_display_roundtrip(dpy);
    close(fd);

    xkb_mod_index_t ctrl_idx = xkb_keymap_mod_get_index(keymap, XKB_MOD_NAME_CTRL);
    uint32_t ctrl_mask = (1 << ctrl_idx);

    // 1. Depress Ctrl modifier (XKB state)
    zwp_virtual_keyboard_v1_modifiers(vk, ctrl_mask, 0, 0, 0);
    wl_display_roundtrip(dpy);
    usleep(15000);

    // 2. Press V (evdev KEY_V = 47)
    zwp_virtual_keyboard_v1_key(vk, 0, 47, WL_KEYBOARD_KEY_STATE_PRESSED);
    wl_display_roundtrip(dpy);
    usleep(25000);

    // 3. Release V
    zwp_virtual_keyboard_v1_key(vk, 0, 47, WL_KEYBOARD_KEY_STATE_RELEASED);
    wl_display_roundtrip(dpy);
    usleep(15000);

    // 4. Release Ctrl modifier
    zwp_virtual_keyboard_v1_modifiers(vk, 0, 0, 0, 0);
    wl_display_roundtrip(dpy);

    zwp_virtual_keyboard_v1_destroy(vk);
    wl_display_disconnect(dpy);
    xkb_keymap_unref(keymap);
    xkb_context_unref(ctx);
    return 0;
}
