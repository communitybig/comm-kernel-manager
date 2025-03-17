#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Progress Dialog for Installation and Removal Operations

This module defines a reusable modal progress dialog for
operations like kernel installation and removal.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib


class ProgressDialog:
    """Modal dialog for showing operation progress."""

    def __init__(
        self,
        parent_window,
        title,
        operation_type,
        target_name,
        complete_callback=None,
        cancel_callback=None,
    ):
        """
        Initialize the progress dialog.

        Args:
            parent_window: Window to set as transient parent
            title: Dialog window title
            operation_type: Type of operation ('install' or 'remove')
            target_name: Name of the target (kernel or driver name)
            complete_callback: Function to call when operation completes
            cancel_callback: Function to call when user cancels
        """
        self.operation_type = operation_type
        self.target_name = target_name
        self.complete_callback = complete_callback
        self.cancel_callback = cancel_callback

        # Create modal window
        self.window = Adw.Window()
        self.window.set_modal(True)
        self.window.set_resizable(False)
        self.window.set_default_size(500, 400)
        self.window.set_title(title)

        # Set transient parent if provided
        if parent_window:
            self.window.set_transient_for(parent_window)

        # Build the UI
        self._build_ui()

    def _build_ui(self):
        """Build the dialog user interface."""
        # Create content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # Operation verb (for UI text)
        verb = "Installing" if self.operation_type == "install" else "Removing"

        # Header
        header = Gtk.Label()
        header.set_markup(f"<b><span size='large'>{verb} {self.target_name}</span></b>")
        header.set_halign(Gtk.Align.START)
        content.append(header)

        # Status label
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.set_margin_top(12)

        status_label_title = Gtk.Label(label="Status:")
        status_label_title.set_halign(Gtk.Align.START)

        self.status_label = Gtk.Label(label=f"Preparing {self.operation_type}ation...")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_hexpand(True)

        status_box.append(status_label_title)
        status_box.append(self.status_label)
        content.append(status_box)

        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Preparing...")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_margin_top(12)
        self.progress_bar.set_margin_bottom(24)
        content.append(self.progress_bar)

        # Terminal output in a frame
        frame = Gtk.Frame()
        frame.set_margin_top(12)

        # Create scrolled window for terminal
        terminal_scroll = Gtk.ScrolledWindow()
        terminal_scroll.set_min_content_height(200)
        terminal_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # Terminal text view
        self.terminal_view = Gtk.TextView()
        self.terminal_view.set_editable(False)
        self.terminal_view.set_cursor_visible(False)
        self.terminal_view.set_monospace(True)
        self.terminal_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.terminal_view.set_left_margin(8)
        self.terminal_view.set_right_margin(8)
        self.terminal_view.set_top_margin(8)
        self.terminal_view.set_bottom_margin(8)
        self.terminal_buffer = self.terminal_view.get_buffer()

        terminal_scroll.set_child(self.terminal_view)
        frame.set_child(terminal_scroll)
        content.append(frame)

        # Button area
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_halign(Gtk.Align.END)
        button_box.set_margin_top(24)

        self.action_button = Gtk.Button(label="Cancel")
        self.action_button.connect("clicked", self._on_cancel_clicked)
        button_box.append(self.action_button)

        content.append(button_box)

        # Set the content of the dialog
        self.window.set_content(content)

    def show(self):
        """Show the dialog."""
        self.window.present()

    def update_progress(self, fraction, text=None):
        """
        Update the progress bar and status label.

        Args:
            fraction: Progress value between 0.0 and 1.0
            text: Status text (optional)
        """
        # Ensure fraction is in valid range
        fraction = max(0.0, min(1.0, fraction))
        self.progress_bar.set_fraction(fraction)

        if text:
            # Format progress text with percentage if needed
            if "%" not in text:
                percentage = fraction * 100
                display_text = f"{text} ({percentage:.1f}%)"
            else:
                display_text = text

            self.progress_bar.set_text(display_text)
            self.status_label.set_text(display_text)
        else:
            # Just show percentage
            percentage = fraction * 100
            self.progress_bar.set_text(f"Progress: {percentage:.1f}%")

    def append_terminal_text(self, text):
        """
        Add text to the terminal output.

        Args:
            text: Text to append to terminal
        """
        if not text:
            return

        # Add newline if needed
        if not text.endswith("\n"):
            text += "\n"

        # Add text to buffer
        end_iter = self.terminal_buffer.get_end_iter()
        self.terminal_buffer.insert(end_iter, text)

        # Auto-scroll
        self._scroll_terminal_to_bottom()

    def _scroll_terminal_to_bottom(self):
        """Scroll terminal view to the bottom."""
        vadj = self.terminal_view.get_vadjustment()
        if vadj:
            GLib.idle_add(
                lambda: vadj.set_value(vadj.get_upper() - vadj.get_page_size())
            )

    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        if self.cancel_callback:
            self.cancel_callback()
        self.destroy()

    def set_complete(self, success):
        """
        Set the dialog to completion state.

        Args:
            success: Whether the operation was successful
        """
        if success:
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("Operation complete!")

            # Update button
            self.action_button.set_label("Close")
            # Disconnect old handler and connect new one
            self.action_button.disconnect_by_func(self._on_cancel_clicked)
            self.action_button.connect("clicked", lambda btn: self.destroy())
            self.action_button.add_css_class("suggested-action")

            # Show success message in terminal
            self.append_terminal_text("\n✅ Operation completed successfully!")
        else:
            self.progress_bar.set_fraction(0.0)
            self.progress_bar.set_text("Operation failed")

            # Update button
            self.action_button.set_label("Close")
            # Disconnect old handler and connect new one
            self.action_button.disconnect_by_func(self._on_cancel_clicked)
            self.action_button.connect("clicked", lambda btn: self.destroy())
            self.action_button.add_css_class("destructive-action")

            # Show error message in terminal
            self.append_terminal_text("\n❌ Operation failed! See details above.")

        # Call complete callback if provided
        if self.complete_callback:
            self.complete_callback(success)

    def destroy(self):
        """Close and destroy the dialog."""
        self.window.destroy()
