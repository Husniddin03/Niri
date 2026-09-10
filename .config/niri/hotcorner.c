#include <gtk/gtk.h>
#include <gtk-layer-shell.h>
#include <stdlib.h>

// Oxirgi marta qachon ishlaganini mikrosaniyalarda saqlash uchun
gint64 last_trigger_time = 0;

gboolean on_enter(GtkWidget *widget, GdkEventCrossing *event, gpointer user_data) {
    gint64 current_time = g_get_monotonic_time() / 1000; // Millisekundga o'giramiz
    
    // Agar oxirgi marta ishlaganidan beri 800ms (0.8 soniya) o'tgan bo'lsagina ishlaydi
    if (current_time - last_trigger_time > 800) {
        last_trigger_time = current_time;
        system("bash ~/.config/niri/overview-toggle.sh &");
    }
    return FALSE;
}

int main(int argc, char *argv[]) {
    gtk_init(&argc, &argv);

    GtkWidget *window = gtk_window_new(GTK_WINDOW_TOPLEVEL);
    
    gtk_layer_init_for_window(GTK_WINDOW(window));
    gtk_layer_set_layer(GTK_WINDOW(window), GTK_LAYER_SHELL_LAYER_TOP);
    
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_TOP, TRUE);
    gtk_layer_set_anchor(GTK_WINDOW(window), GTK_LAYER_SHELL_EDGE_LEFT, TRUE);
    
    gtk_window_set_default_size(GTK_WINDOW(window), 2, 2);
    gtk_layer_set_keyboard_interactivity(GTK_WINDOW(window), FALSE);

    GtkCssProvider *provider = gtk_css_provider_new();
    gtk_css_provider_load_from_data(provider, "window { background: transparent; border: none; }", -1, NULL);
    gtk_style_context_add_provider_for_screen(gdk_screen_get_default(), GTK_STYLE_PROVIDER(provider), GTK_STYLE_PROVIDER_PRIORITY_APPLICATION);

    g_signal_connect(window, "enter-notify-event", G_CALLBACK(on_enter), NULL);
    g_signal_connect(window, "destroy", G_CALLBACK(gtk_main_quit), NULL);

    gtk_widget_show_all(window);
    gtk_main();

    return 0;
}