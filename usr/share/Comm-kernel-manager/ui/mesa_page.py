#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Mesa Drivers Management Page

This module defines the UI for Mesa drivers management, allowing users
to install and switch between different Mesa driver versions.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from core.mesa_manager import MesaManager


class MesaPage(Gtk.Box):
    """Page for Mesa drivers management."""

    def __init__(self):
        """Initialize the Mesa drivers management page."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        
        # Initialize Mesa manager
        self.mesa_manager = MesaManager()
        
        # Create content
        self._create_content()
        
        # Load available Mesa drivers
        self._load_mesa_drivers()
    
    def _create_content(self):
        """Create the UI elements for Mesa drivers management with fixed layout."""
        # Create main container as scrolled window to maintain fixed window size
        main_scrolled = Gtk.ScrolledWindow()
        main_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scrolled.set_min_content_height(550)  # Adjust to match your window height
        main_scrolled.set_vexpand(True)
        
        # Main content box inside scrolled window
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        
        # Create a ClampView to constrain content width for better readability
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_tightening_threshold(600)
        
        # Inner content container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
        # Create a preference group for the drivers
        driver_group = Adw.PreferencesGroup()
        driver_group.set_title("Video Drivers")
        driver_group.set_description("Select a video driver version to use")
        
        # Add info button as a header suffix
        info_button = Gtk.Button.new_from_icon_name("help-about-symbolic")
        info_button.set_tooltip_text("Information about video drivers")
        info_button.set_valign(Gtk.Align.CENTER)
        info_button.connect("clicked", self._on_help_clicked)
        driver_group.set_header_suffix(info_button)
        
        # Create a scrolled window for drivers that will resize itself
        self.drivers_scrolled = Gtk.ScrolledWindow()
        self.drivers_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.drivers_scrolled.set_vexpand(True)
        # Important: Start with a larger height, will shrink when progress appears
        self.drivers_scrolled.set_min_content_height(300)
        
        # Create a card for the driver options inside the scrolled window
        driver_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        driver_card.add_css_class("card")
        driver_card.set_margin_top(12)
        driver_card.set_margin_start(12)
        driver_card.set_margin_end(12)
        driver_card.set_margin_bottom(12)
        driver_card.set_vexpand(False)
        
        # Create checkbuttons for the driver options
        self.driver_group = None
        self.driver_buttons = {}
        
        self.drivers_scrolled.set_child(driver_card)
        driver_group.add(self.drivers_scrolled)
        self.driver_box = driver_card
        driver_group.set_vexpand(False)
        
        # Add the driver group to the content
        content_box.append(driver_group)
        
        # Add apply button in a button box for better centering
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(16)
        button_box.set_vexpand(False)
        
        self.apply_button = Gtk.Button.new_with_label("Apply Changes")
        self.apply_button.add_css_class("suggested-action")
        self.apply_button.connect("clicked", self._on_apply_clicked)
        button_box.append(self.apply_button)
        
        content_box.append(button_box)
        
        # Progress section (initially hidden)
        progress_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        progress_card.add_css_class("card")
        progress_card.set_margin_top(16)
        progress_card.set_spacing(8)
        
        self.progress_label = Gtk.Label.new("Applying Changes")
        self.progress_label.set_halign(Gtk.Align.START)
        self.progress_label.set_margin_start(16)
        self.progress_label.set_margin_top(12)
        progress_card.append(self.progress_label)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_margin_start(16)
        self.progress_bar.set_margin_end(16)
        self.progress_bar.set_margin_bottom(16)
        progress_card.append(self.progress_bar)
        
        content_box.append(progress_card)
        
        # Progress card is initially hidden
        progress_card.set_visible(False)
        self.progress_container = progress_card
        
        # Set the clamp's child to the content box
        clamp.set_child(content_box)
        main_box.append(clamp)
        
        # Set the main box as the child of the scrolled window
        main_scrolled.set_child(main_box)
        
        # Add the main scrolled window to this widget
        self.append(main_scrolled)

    def _show_progress_container(self):
        """Show the progress container and adjust layout."""
        if not self.progress_container.get_visible():
            self.progress_container.set_visible(True)
            # Reduce the driver list size when progress container appears
            self.drivers_scrolled.set_min_content_height(350)
    
    def _hide_progress_container(self):
        """Hide the progress container and restore layout."""
        # Delay hiding to let animations complete
        GLib.timeout_add(100, self._actually_hide_progress_container)
        return False

    def _actually_hide_progress_container(self):
        """Actually hide the progress container."""
        self.progress_container.set_visible(False)
        # Restore the driver list to full size
        self.drivers_scrolled.set_min_content_height(450)
        return False
    
    def _load_mesa_drivers(self):
        """Load available Mesa drivers from the Mesa manager."""
        # Clear existing items
        while True:
            child = self.driver_box.get_first_child()
            if child is None:
                break
            self.driver_box.remove(child)
        
        # Get available drivers
        drivers = self.mesa_manager.get_available_drivers()
        
        # Create first radio button (will be the group leader)
        first_button = None
        
        # Add drivers to the list using a more modern approach with ActionRows
        for driver in drivers:
            # Create a row for better visual presentation
            row = Adw.ActionRow()
            row.set_title(driver["name"])
            
            if "description" in driver:
                row.set_subtitle(driver["description"])
            
            # Add icon based on driver type
            icon_name = "video-display-symbolic"
            if "git" in driver["id"]:
                icon_name = "weather-storm-symbolic"  # More cutting-edge
            elif "amber" in driver["id"]:
                icon_name = "emblem-default-symbolic"  # More stable
                
            icon = Gtk.Image.new_from_icon_name(icon_name)
            row.add_prefix(icon)
            
            # Create radio button and add to row
            button = Gtk.CheckButton()
            
            # Set up the button group
            if first_button is None:
                first_button = button
            else:
                button.set_group(first_button)
            
            # Store the button
            self.driver_buttons[driver["id"]] = button
            
            # Mark the active driver
            if driver.get("active", False):
                button.set_active(True)
                
                # Add "Active" tag using a styled label instead of Pill
                active_tag = Gtk.Label.new("Active")
                active_tag.add_css_class("success")
                active_tag.add_css_class("caption")
                active_tag.set_margin_start(4)
                active_tag.set_margin_end(4)
                
                active_box = Gtk.Box()
                active_box.add_css_class("card")
                active_box.add_css_class("success")
                active_box.set_margin_start(4)
                active_box.set_margin_end(8)
                active_box.append(active_tag)
                
                row.add_suffix(active_box)
            
            row.add_prefix(button)
            self.driver_box.append(row)
    
    def _on_refresh_clicked(self, button):
        """Callback for refresh button click."""
        self._load_mesa_drivers()
    
    def _on_help_clicked(self, button):
        """Show information dialog about the drivers."""
        # Compatible with older libadwaita
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading("Video Drivers Information")
        dialog.set_body(
            "Different driver versions offer various features and performance characteristics:\n\n"
            "• Amber: Stable and well-tested version\n"
            "• Stable: Regular Mesa release\n"
            "• Tkg-Stable: Enhanced performance build\n"
            "• Tkg-git: Latest development version with cutting-edge features\n\n"
            "Choose the one that best fits your needs and hardware."
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        dialog.present()
    
    def _on_apply_clicked(self, button):
        """Apply the selected driver changes."""
        # Find which driver is selected
        selected_driver = None
        for driver_id, button in self.driver_buttons.items():
            if button.get_active():
                selected_driver = driver_id
                break
        
        if selected_driver is None:
            return
        
        # Show a confirmation dialog to prevent accidental changes - compatible with older libadwaita
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading("Apply Driver Changes")
        dialog.set_body(f"Are you sure you want to apply the selected driver changes?\n\nThis will modify your system's video drivers and might require a reboot.")
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("apply", "Apply Changes")
        dialog.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        # Connect the response signal
        dialog.connect("response", self._on_confirm_dialog_response, selected_driver)
        
        # Show the dialog
        dialog.present()
    
    def _on_confirm_dialog_response(self, dialog, response, selected_driver):
        """Handle the confirmation dialog response."""
        if response != "apply":
            return
        
        # Show progress bar
        self._show_progress_container()
        self.progress_bar.set_fraction(0.0)
        self.progress_label.set_text(f"Applying {selected_driver} driver")
        self.progress_bar.set_text("Preparing...")
        
        # Disable button during operation
        self.apply_button.set_sensitive(False)
        
        # Start installation in a separate thread to avoid UI freezing
        self.mesa_manager.apply_driver(
            selected_driver,
            progress_callback=self._update_progress,
            complete_callback=lambda success: GLib.idle_add(
                self._application_complete, success
            )
        )
    
    def _update_progress(self, fraction, text=None):
        """
        Update the progress bar.
        
        Args:
            fraction: Progress fraction (0.0 to 1.0).
            text: Optional text to display.
        """
        GLib.idle_add(self._update_progress_idle, fraction, text)
    
    def _update_progress_idle(self, fraction, text):
        """Update progress bar from main thread."""
        self.progress_bar.set_fraction(fraction)
        if text:
            self.progress_bar.set_text(text)
        
        # Make sure the progress container is visible when updating
        if not self.progress_container.get_visible():
            self.progress_container.set_visible(True)
            
        return False  # Don't call again
    
    def _application_complete(self, success):
        """Handle application completion."""
        # Re-enable button
        self.apply_button.set_sensitive(True)
        
        # Update progress
        if success:
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("Changes applied successfully!")
            
            # Show completion dialog
            self._show_completion_dialog(
                "Driver Changed Successfully", 
                "The video driver was changed successfully.\nYou may need to reboot your system for changes to take effect.",
                "success"
            )
        else:
            self.progress_bar.set_text("Failed to apply changes.")
            
            # Show failure dialog
            self._show_completion_dialog(
                "Failed to Change Driver", 
                "The driver change operation failed. Please check the system logs for details.",
                "error"
            )
        
        # Refresh driver list
        self._load_mesa_drivers()
        
        return False
    
    def _show_completion_dialog(self, title, message, status):
        """Show a completion dialog with OK button."""
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(title)
        dialog.set_body(message)
        
        # Add icon based on status
        if hasattr(dialog, 'set_icon_name'):  # Check if method exists
            if status == "success":
                dialog.set_icon_name("emblem-ok-symbolic")
            else:
                dialog.set_icon_name("dialog-error-symbolic")
        
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.set_close_response("ok")
        
        # Connect close response to hide progress container
        dialog.connect("response", lambda d, r: self._hide_progress_container())
        
        dialog.present()
    
    def _hide_progress_bar(self):
        """Hide the progress bar."""
        # Wait a short time to ensure animations are complete
        GLib.timeout_add(100, self._actually_hide_progress_bar)
        return False  # Don't call again
    
    def _actually_hide_progress_bar(self):
        """Actually hide the progress container after a short delay."""
        self.progress_container.set_visible(False)
        return False  # Don't call again
    
    def _find_toast_overlay(self):
        """Find the nearest ToastOverlay in the widget hierarchy."""
        # Try to find a toast overlay in the hierarchy
        widget = self
        while widget:
            if isinstance(widget, Adw.ToastOverlay):
                return widget
            parent = widget.get_parent()
            if parent is None:
                # Try to get the root widget
                root = widget.get_root()
                if root and hasattr(root, "get_content"):
                    content = root.get_content()
                    # Check if content is a toast overlay or contains one
                    if isinstance(content, Adw.ToastOverlay):
                        return content
                    # Try to find a toast overlay in the content
                    if hasattr(content, "get_first_child"):
                        child = content.get_first_child()
                        while child:
                            if isinstance(child, Adw.ToastOverlay):
                                return child
                            child = child.get_next_sibling()
                break
            widget = parent
        
        # Fall back to checking if we have a window with a toast overlay
        window = self.get_root()
        if window:
            content = window.get_content()
            while content:
                if isinstance(content, Adw.ToastOverlay):
                    return content
                if hasattr(content, "get_content"):
                    content = content.get_content()
                else:
                    break
        
        # No toast overlay found
        return None