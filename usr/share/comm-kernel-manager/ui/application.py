#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Application Class

This module defines the main application class for the Kernel Manager.
"""

import os
import json
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw, Gdk

from ui.window import KernelManagerWindow


class SettingsManager:
    """Settings manager for the Kernel Manager application."""
    
    def __init__(self):
        """Initialize the settings manager."""
        self.settings_file = os.path.expanduser("~/.config/kernel-manager/settings.json")
        os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
        self.json_config = self._load_settings()
    
    def _load_settings(self):
        """Load settings from file."""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
        return {}
    
    def _save_settings(self):
        """Save settings to file."""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.json_config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def load_setting(self, key, default=None):
        """Load a setting value."""
        return self.json_config.get(key, default)
    
    def save_setting(self, key, value):
        """Save a setting value."""
        self.json_config[key] = value
        return self._save_settings()


class KernelManagerApplication(Adw.Application):
    """Main application class for Kernel Manager."""

    def __init__(self):
        """Initialize the application."""
        super().__init__(application_id="org.manjaro.kernelmanager",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)
        
        # Initialize settings manager
        self.settings_manager = SettingsManager()
        
        # Load custom CSS
        self._load_css()  # Adicionada esta linha

    def _load_css(self):
        """Load custom CSS styling from file."""
        css_provider = Gtk.CssProvider()
        
        # Get the path to the CSS file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        css_path = os.path.join(base_dir, "assets", "css", "style.css")
        
        try:
            css_provider.load_from_path(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            print(f"Loaded CSS from {css_path}")
        except Exception as e:
            print(f"Error loading CSS: {e}")

    def on_activate(self, app):
        """
        Callback for the application activation.
        
        Args:
            app: The application instance.
        """
        # Create the main window and present it
        win = KernelManagerWindow(application=app)
        win.present()
        
    def show_error_dialog(self, message):
        """Show an error dialog with the given message."""
        dialog = Adw.MessageDialog.new(self.get_active_window())
        dialog.set_heading("Error")
        dialog.set_body(message)
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present()