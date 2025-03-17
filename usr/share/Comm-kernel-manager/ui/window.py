#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Main Window

This module defines the main application window with tabs for
kernel and Mesa driver management.
"""

import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk

from ui.kernel_page import KernelPage
from ui.mesa_page import MesaPage


class KernelManagerWindow(Adw.ApplicationWindow):
    """Main window for the Kernel Manager application."""

    def __init__(self, **kwargs):
        """Initialize the main window with tabs for different functionalities."""
        super().__init__(**kwargs)
        
        # Set up window properties
        self.set_title("Kernel Manager")
        self.set_default_size(800, 630)
        self.set_resizable(False)  # IMPORTANT: Lock window resizing
        
        # Initialize settings if needed
        self._init_settings()
        
        # Main container for the application - use BoxLayout to ensure proper expanding
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Create overlay for backdrop effect
        self.overlay = Gtk.Overlay()
        main_box.append(self.overlay)
        
        # Create backdrop for dimming when dialog is open
        self.backdrop = Gtk.Box()
        self.backdrop.set_hexpand(True)
        self.backdrop.set_vexpand(True)
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
            box.backdrop {
                background-color: rgba(0, 0, 0, 0.5);
            }
        """.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.backdrop.add_css_class("backdrop")
        self.backdrop.set_visible(False)  # Inicialmente invisível
        
        # Create main content using Adw.ToolbarView for modern GNOME look
        # This will contain the content that should always be visible and expand
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_vexpand(True)  # This is crucial to ensure content expands
        
        content = Adw.ToolbarView()
        
        # Create header bar with title
        header = Adw.HeaderBar()
        # Add refresh button to header
        refresh_button = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_button.set_tooltip_text("Refresh")
        refresh_button.set_valign(Gtk.Align.CENTER)
        header.pack_end(refresh_button)
        
        # Create stack for separating kernel and Mesa management
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(200)
        self.stack.set_vexpand(True)
        
        # Create pages
        kernel_page = KernelPage()
        mesa_page = MesaPage()
        
        # Add pages to the stack
        self.stack.add_titled(kernel_page, "kernel", "Kernel")
        self.stack.add_titled(mesa_page, "mesa", "Mesa Drivers")
        
        # Create a stack switcher for navigation
        stack_switcher = Gtk.StackSwitcher()
        stack_switcher.set_stack(self.stack)
        stack_switcher.set_halign(Gtk.Align.CENTER)
        
        # Set the stack switcher as the title widget in the header
        header.set_title_widget(stack_switcher)
        
        # Connect refresh button to page refresh methods
        refresh_button.connect("clicked", 
                            lambda button: kernel_page._on_refresh_clicked(button) 
                            if self.stack.get_visible_child_name() == "kernel" 
                            else mesa_page._on_refresh_clicked(button))
        
        # Set up the content structure
        content.add_top_bar(header)
        
        # Create toast overlay for notifications
        toast_overlay = Adw.ToastOverlay()
        toast_overlay.set_child(self.stack)
        content.set_content(toast_overlay)
        
        # Add content to content box
        content_box.append(content)
        content_box.set_vexpand(True)
        
        # Add content to overlay
        self.overlay.set_child(content_box)
        self.overlay.add_overlay(self.backdrop)
        
        # Set the content of the window
        self.set_content(main_box)
        
        # Initialize stack-specific connections
        self._setup_stack_connections()
        
        # Show warning popup on startup if enabled
        GLib.idle_add(self._check_show_warning_dialog)
        
    def _init_settings(self):
        """Initialize settings for the application."""
        # Check if application has settings manager
        if hasattr(self.get_application(), "settings_manager"):
            self.settings_manager = self.get_application().settings_manager
        else:
            # Create a simple settings mechanism if not available
            self.settings_manager = SimpleSettingsManager()
    
    def _setup_stack_connections(self):
        """Set up stack-specific connections and behavior."""
        # Connect to the notify::visible-child signal for Gtk.Stack
        self.stack.connect("notify::visible-child", self._on_stack_changed)
        
    def _on_stack_changed(self, stack, pspec):
        """Handle stack page change event."""
        # Currently no specific actions needed here
        pass
    
    def _check_show_warning_dialog(self):
        """Check whether to show the warning dialog on startup."""
        try:
            show_warning = self.settings_manager.load_setting("show-kernel-warning-on-startup", True)
            if show_warning:
                self.show_warning_dialog()
        except Exception as e:
            print(f"Error checking warning dialog setting: {str(e)}")
            # Default to showing the dialog if there's an error
            self.show_warning_dialog()
        return False  # Don't repeat
    
    def show_warning_dialog(self):
        """Show a detailed warning dialog about kernel and Mesa changes."""
        # Mostrar o backdrop
        self.backdrop.set_visible(True)
        
        # Create a dialog window properly using Adw.Window
        dialog = Adw.Window()
        dialog.set_default_size(700, 500)
        dialog.set_modal(True)
        dialog.set_transient_for(self)
        dialog.set_hide_on_close(True)
        
        # Create content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Add header bar
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(Gtk.Label(label="Kernel and Mesa Management"))
        content_box.append(header_bar)
        
        # Create main box to hold everything with proper layout
        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer_box.set_vexpand(True)
        
        # Create scrolled window for content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_margin_top(12)
        main_box.set_spacing(12)
        
        # Warning header with icon
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        header_box.set_margin_bottom(16)
        
        warning_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        warning_icon.set_pixel_size(32)
        warning_icon.add_css_class("warning")
        
        header_label = Gtk.Label()
        header_label.set_markup("<b>Important Information About Kernel and Mesa Changes</b>")
        header_label.set_wrap(True)
        header_label.set_xalign(0)
        
        header_box.append(warning_icon)
        header_box.append(header_label)
        main_box.append(header_box)
        
        # Introduction text
        intro_label = Gtk.Label()
        intro_label.set_wrap(True)
        intro_label.set_xalign(0)
        intro_label.set_margin_bottom(16)
        intro_label.set_markup(
            "Changing your system's kernel or Mesa drivers can impact system stability. "
            "Please proceed with caution and understand the following risks and recommendations:"
        )
        main_box.append(intro_label)
        
        # Kernel section
        kernel_title = Gtk.Label()
        kernel_title.set_markup("<b>Kernel Management</b>")
        kernel_title.set_xalign(0)
        kernel_title.set_margin_top(12)
        main_box.append(kernel_title)
        
        kernel_items = [
            "• <b>Always keep at least one working kernel</b> installed as a fallback",
            "• LTS kernels offer better stability, while newer kernels provide newer hardware support",
            "• Test your system thoroughly after kernel changes",
            "• If a new kernel causes issues, you can select the previous kernel from the boot menu",
            "• Real-time (RT) kernels are specialized for low-latency tasks but may not be suitable for general use"
        ]
        
        for item in kernel_items:
            item_label = Gtk.Label()
            item_label.set_wrap(True)
            item_label.set_xalign(0)
            item_label.set_markup(item)
            item_label.set_margin_start(12)
            item_label.set_margin_bottom(4)
            main_box.append(item_label)
        
        # Mesa section
        mesa_title = Gtk.Label()
        mesa_title.set_markup("<b>Mesa Driver Management</b>")
        mesa_title.set_xalign(0)
        mesa_title.set_margin_top(16)
        main_box.append(mesa_title)
        
        mesa_items = [
            "• Mesa drivers provide 3D graphics acceleration for AMD, Intel, and some NVIDIA GPUs",
            "• Changing Mesa versions may affect graphics performance and application compatibility",
            "• The stable version is recommended for most users",
            "• Development versions may offer better performance but with less stability",
            "• If graphics issues occur after a change, you can switch back to the previous driver"
        ]
        
        for item in mesa_items:
            item_label = Gtk.Label()
            item_label.set_wrap(True)
            item_label.set_xalign(0)
            item_label.set_markup(item)
            item_label.set_margin_start(12)
            item_label.set_margin_bottom(4)
            main_box.append(item_label)
        
        # General advice
        advice_label = Gtk.Label()
        advice_label.set_wrap(True)
        advice_label.set_xalign(0)
        advice_label.set_margin_top(16)
        advice_label.set_markup(
            "<b>General Advice:</b> Consider creating a system backup before making changes. "
            "If you're not sure which option to choose, the LTS kernel and stable Mesa drivers "
            "are generally the safest choices for most users."
        )
        main_box.append(advice_label)
        
        # Add main box to scrolled window
        scrolled.set_child(main_box)
        outer_box.append(scrolled)
        
        # Create bottom area with fixed height
        bottom_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        bottom_area.set_margin_start(24)
        bottom_area.set_margin_end(24)
        bottom_area.set_margin_top(12)
        bottom_area.set_margin_bottom(12)
        
        # Add separator above bottom area
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        bottom_area.append(separator)
        
        # Create a box for controls with spacing
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        controls_box.set_margin_top(12)
        controls_box.set_margin_bottom(12)
        
        # Get current setting value
        current_value = self.settings_manager.load_setting("show-kernel-warning-on-startup", True)
        
        # Create switch with label
        switch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        switch_box.set_hexpand(True)
        
        switch_label = Gtk.Label(label="Show this warning on startup")
        switch_label.set_halign(Gtk.Align.START)
        
        show_on_startup_switch = Gtk.Switch()
        show_on_startup_switch.set_active(current_value)
        show_on_startup_switch.set_valign(Gtk.Align.CENTER)
        
        switch_box.append(switch_label)
        switch_box.append(show_on_startup_switch)
        controls_box.append(switch_box)
        
        # Add close button
        close_button = Gtk.Button(label="Close")
        close_button.add_css_class("pill")
        close_button.add_css_class("suggested-action")
        close_button.connect("clicked", lambda btn: self._close_dialog(dialog))
        close_button.set_halign(Gtk.Align.END)
        controls_box.append(close_button)
        
        bottom_area.append(controls_box)
        outer_box.append(bottom_area)
        
        content_box.append(outer_box)
        
        # Set content and present dialog
        dialog.set_content(content_box)
        
        # Connect the switch signal
        show_on_startup_switch.connect("notify::active", self._on_warning_switch_toggled)
        
        # Conectar o evento de fechamento da janela
        dialog.connect("close-request", self._on_dialog_closed)
        
        dialog.present()
    
    def _close_dialog(self, dialog):
        """Fechar o diálogo e esconder o backdrop"""
        self.backdrop.set_visible(False)
        dialog.close()
    
    def _on_dialog_closed(self, dialog):
        """Manipular o evento de fechamento do diálogo"""
        self.backdrop.set_visible(False)
        return False
    
    def _on_warning_switch_toggled(self, switch, param):
        """Handle toggling the switch in the warning dialog."""
        try:
            value = switch.get_active()
            
            # Print debug information
            print(f"Attempting to save setting: show-kernel-warning-on-startup = {value}")
            
            # Update setting
            success = self.settings_manager.save_setting("show-kernel-warning-on-startup", value)
            
            if success:
                print(f"Successfully saved setting: show-kernel-warning-on-startup = {value}")
            else:
                print("Warning: Setting may not have been saved properly.")
                
        except Exception as e:
            # Log the error
            print(f"Error toggling warning dialog setting: {str(e)}")
            
            # Fallback approach - try direct save
            try:
                settings_file = os.path.expanduser("~/.config/kernel-manager/settings.json")
                os.makedirs(os.path.dirname(settings_file), exist_ok=True)
                
                # Load existing settings if available
                settings = {}
                if os.path.exists(settings_file):
                    with open(settings_file, 'r') as f:
                        import json
                        try:
                            settings = json.load(f)
                        except:
                            settings = {}
                
                # Update the setting
                settings["show-kernel-warning-on-startup"] = switch.get_active()
                
                # Write back to file
                with open(settings_file, 'w') as f:
                    import json
                    json.dump(settings, f, indent=2)
                    
                print(f"Saved setting using fallback method to: {settings_file}")
            except Exception as backup_error:
                print(f"Even fallback saving method failed: {str(backup_error)}")


class SimpleSettingsManager:
    """Simple settings manager for the application when no global one is available."""
    
    def __init__(self):
        """Initialize the settings manager."""
        self.settings_file = os.path.expanduser("~/.config/kernel-manager/settings.json")
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Load settings from file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    import json
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
        return {}
    
    def _save_settings(self):
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                import json
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def load_setting(self, key, default=None):
        """Load a setting value."""
        return self.settings.get(key, default)
    
    def save_setting(self, key, value):
        """Save a setting value."""
        self.settings[key] = value
        return self._save_settings()