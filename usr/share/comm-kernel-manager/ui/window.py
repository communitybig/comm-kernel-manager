#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Main Window

This module defines the main application window for the Kernel Manager.
"""

import os
import json
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from ui.kernel_page import KernelPage
from ui.mesa_page import MesaPage


class KernelManagerWindow(Adw.ApplicationWindow):
    """Main window for the Kernel Manager application."""

    def __init__(self, **kwargs):
        """Initialize the main window with content."""
        super().__init__(**kwargs)

        # Set up window properties
        self.set_default_size(800, 630)

        # Create the toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()

        # Create the toolbar view first (fix parent widget issue)
        self.toolbar = Adw.ToolbarView()

        # Set the toolbar as the child of the toast overlay
        self.toast_overlay.set_child(self.toolbar)

        # Create a simple content stack using Adw.ViewStack
        self.content = Adw.ViewStack()

        # Set the content stack as the content of the toolbar view
        self.toolbar.set_content(self.content)

        # Create the header bar with view switcher
        self._setup_header()

        # Create tabs (pages) for the different functionalities
        self._setup_pages()

        # Set the window content
        self.set_content(self.toast_overlay)

        # Initialize settings and check for warning dialog
        self._init_settings()
        GLib.idle_add(self._check_show_warning)

    def _setup_pages(self):
        """Set up the main content pages."""
        # Create and add the kernel management page
        kernel_page = KernelPage()
        self.content.add_titled_with_icon(
            kernel_page, "kernel", "Kernel", "system-run-symbolic"
        )

        # Create and add the Mesa drivers page
        mesa_page = MesaPage()
        self.content.add_titled_with_icon(
            mesa_page, "mesa", "Mesa Drivers", "preferences-system-details-symbolic"
        )

        # Store reference to pages
        self.kernel_page = kernel_page
        self.mesa_page = mesa_page

    def _setup_header(self):
        """Set up the header bar with view switcher."""
        # Create the header bar
        header = Adw.HeaderBar()

        # Create view switcher
        switcher = Adw.ViewSwitcher()
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        switcher.set_stack(self.content)
        header.set_title_widget(switcher)

        # Refresh button removed as requested

        # Add header to the toolbar view
        self.toolbar.add_top_bar(header)

    def _init_settings(self):
        """Initialize settings for the application."""
        app = self.get_application()
        if hasattr(app, "settings_manager"):
            # Use the application's settings manager
            self.settings = app.settings_manager
        else:
            # Create a local settings manager as fallback
            self.settings = SettingsAdapter()

    def _check_show_warning(self):
        """Check whether to show the warning dialog."""
        try:
            # Use load_setting instead of get to match SettingsManager API
            show_warning = self.settings.load_setting(
                "show-kernel-warning-on-startup", True
            )
            if show_warning:
                self._show_warning_dialog()
        except Exception as e:
            print(f"Error checking warning dialog setting: {e}")
        return False  # Don't call again

    def _show_warning_dialog(self):
        """Show warning dialog about kernel and mesa modifications."""
        dialog = Adw.AlertDialog()
        dialog.set_heading("Warning: System Modifications")

        # Create the main message
        message = (
            "Changing kernels or drivers can impact system stability.\n\n"
            "<b>Kernel Management</b>\n"
            "• Always keep at least one working kernel installed\n"
            "• LTS kernels offer better stability\n"
            "• Real-time kernels are specialized for specific tasks\n\n"
            "<b>Mesa Driver Management</b>\n"
            "• Stable versions are recommended for most users\n"
            "• Development versions may have issues with some applications\n\n"
            "Consider backing up your system before making changes."
        )

        dialog.set_body(message)
        dialog.set_body_use_markup(True)

        # Add responses
        dialog.add_response("ok", "I Understand")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")

        # Add "don't show again" checkbox
        check = Gtk.CheckButton()
        check.set_label("Don't show this warning next time")
        check.set_margin_top(12)
        check.connect("toggled", self._on_dont_show_toggled)
        dialog.set_extra_child(check)

        dialog.present(self)

    def _on_dont_show_toggled(self, check):
        """Handle checkbox toggle for the warning dialog."""
        # Use save_setting instead of set to match SettingsManager API
        show_warning = not check.get_active()
        self.settings.save_setting("show-kernel-warning-on-startup", show_warning)

    def add_toast(self, message, timeout=3):
        """Show a toast notification."""
        toast = Adw.Toast.new(message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)


class SettingsAdapter:
    """Adapter for the Settings class to match SettingsManager API."""

    def __init__(self):
        """Initialize settings adapter."""
        self.path = os.path.expanduser("~/.config/kernel-manager/settings.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self.data = self._load()

    def _load(self):
        """Load settings from file."""
        try:
            if os.path.exists(self.path):
                with open(self.path, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {}

    def _save(self):
        """Save settings to file."""
        try:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def load_setting(self, key, default=None):
        """Load a setting value - matches SettingsManager API."""
        return self.data.get(key, default)

    def save_setting(self, key, value):
        """Save a setting value - matches SettingsManager API."""
        self.data[key] = value
        return self._save()
