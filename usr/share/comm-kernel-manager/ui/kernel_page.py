#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Kernel Management Page

This module defines the UI for kernel management, allowing users
to install and manage different kernel versions.
"""

import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, GObject

from core.kernel_manager import KernelManager
from ui.dialogs.progress_dialog import ProgressDialog


class KernelModel(GObject.Object):
    """Model for kernel data in column view."""

    # Define GObject properties
    id = GObject.Property(type=str, default="")
    name = GObject.Property(type=str, default="Unknown")
    version = GObject.Property(type=str, default="Unknown")
    is_lts = GObject.Property(type=bool, default=False)
    is_rt = GObject.Property(type=bool, default=False)
    installed = GObject.Property(type=bool, default=False)
    running = GObject.Property(type=bool, default=False)

    def __init__(self, kernel_dict):
        super().__init__()
        self.original_data = kernel_dict

        # Set properties from dictionary data
        self.set_property("id", kernel_dict.get("id", ""))
        self.set_property("name", kernel_dict.get("name", "Unknown"))
        self.set_property("version", kernel_dict.get("version", "Unknown"))
        self.set_property(
            "is_lts",
            "-lts" in kernel_dict.get("name", "").lower()
            or kernel_dict.get("lts", False),
        )
        self.set_property(
            "is_rt",
            "rt" in kernel_dict.get("name", "").lower() or kernel_dict.get("rt", False),
        )
        self.set_property("installed", kernel_dict.get("installed", False))
        self.set_property("running", kernel_dict.get("running", False))


class KernelPage(Gtk.Box):
    """Page for kernel management."""

    def __init__(self):
        """Initialize the kernel management page."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Setup main UI components
        self._setup_ui()

        # Create the ColumnView for displaying kernels as a table
        self._create_column_view()

        # Initialize kernel data loading
        self._show_loading_ui()
        GLib.idle_add(self._load_kernels)

    def _setup_ui(self):
        """Setup the main UI components."""
        # Scroll container
        self.scroll = Gtk.ScrolledWindow(
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )

        # Content box with width limit
        self.content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_bottom=24,
            margin_start=12,
            margin_end=12,
        )

        # Set maximum width to 800px
        self.content.set_size_request(800, -1)  # Width: 800px, Height: natural
        self.content.set_halign(Gtk.Align.CENTER)  # Center the content box

        self.scroll.set_child(self.content)
        self.append(self.scroll)

        # Initialize kernel manager
        self.kernel_manager = KernelManager()
        self.loading_page = None

    def _create_column_view(self):
        """Create the column view for displaying kernels."""
        # Create the container box
        self.kernel_list_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
            margin_top=8,
        )

        # Set up store and models
        self.store = Gio.ListStore(item_type=KernelModel)

        # Create sorter and connect it properly to enable column header sorting
        self.sorter = Gtk.MultiSorter.new()
        self.sort_model = Gtk.SortListModel.new(self.store, self.sorter)
        self.selection = Gtk.SingleSelection.new(self.sort_model)

        # Create the column view with the proper sort mechanism
        self.column_view = Gtk.ColumnView.new(self.selection)
        self.column_view.add_css_class("card")
        self.column_view.set_show_row_separators(True)
        self.column_view.set_show_column_separators(True)

        # Important: Connect the sorter to the column view so clicks work
        self.column_view.set_model(self.selection)
        self.column_view.set_halign(Gtk.Align.CENTER)

        # Add the columns with a simplified approach
        self._add_columns()

        # Add to scrolled window
        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled_window.set_child(self.column_view)
        self.kernel_list_box.append(scrolled_window)

        # Add to main content
        self.content.append(self.kernel_list_box)

    def _add_columns(self):
        """Add columns to the column view with appropriate sorters."""
        # Create expression objects for properties
        name_expr = Gtk.PropertyExpression.new(KernelModel.__gtype__, None, "name")
        version_expr = Gtk.PropertyExpression.new(
            KernelModel.__gtype__, None, "version"
        )
        lts_expr = Gtk.PropertyExpression.new(KernelModel.__gtype__, None, "is_lts")
        rt_expr = Gtk.PropertyExpression.new(KernelModel.__gtype__, None, "is_rt")
        installed_expr = Gtk.PropertyExpression.new(
            KernelModel.__gtype__, None, "installed"
        )
        running_expr = Gtk.PropertyExpression.new(
            KernelModel.__gtype__, None, "running"
        )

        # Add Name column
        self._add_text_column("Package Name", True, name_expr, self._bind_name_cell)

        # Add Version column
        self._add_text_column("Version", False, version_expr, self._bind_version_cell)

        # Add Type column
        type_factory = Gtk.SignalListItemFactory.new()
        type_factory.connect("setup", self._setup_type_cell)
        type_factory.connect("bind", self._bind_type_cell)

        type_sorter = Gtk.MultiSorter.new()
        type_sorter.append(Gtk.NumericSorter.new(lts_expr))
        type_sorter.append(Gtk.NumericSorter.new(rt_expr))

        type_column = Gtk.ColumnViewColumn.new("Type", type_factory)
        type_column.set_resizable(True)
        type_column.set_sorter(type_sorter)
        self.column_view.append_column(type_column)

        # Add Action column (not sortable)
        action_factory = Gtk.SignalListItemFactory.new()
        action_factory.connect("setup", self._setup_action_cell)
        action_factory.connect("bind", self._bind_action_cell)
        action_column = Gtk.ColumnViewColumn.new("Action", action_factory)
        action_column.set_resizable(True)
        self.column_view.append_column(action_column)

    def _add_text_column(self, title, expand, expr, bind_func):
        """Helper to add a text column with sorting."""
        factory = Gtk.SignalListItemFactory.new()
        factory.connect("setup", self._setup_text_cell)
        factory.connect("bind", bind_func)

        column = Gtk.ColumnViewColumn.new(title, factory)
        column.set_resizable(True)
        if expand:
            column.set_expand(True)

        # Create sorter based on property name (simplify the type check)
        if isinstance(expr, Gtk.PropertyExpression):
            # Just assume string sorter is appropriate for most cases
            # This avoids the need for get_expression_type()
            if title.lower() == "status":
                # Special case for status column
                sorter = Gtk.NumericSorter.new(expr)
            else:
                sorter = Gtk.StringSorter.new(expr)

            column.set_sorter(sorter)

        # Connect to sorter changed event
        column.connect("notify::sorter-order", self._on_sort_changed)

        self.column_view.append_column(column)
        return column

    def _on_sort_changed(self, column, pspec):
        """Handle column header click for sorting."""
        # Get all columns
        columns = self.column_view.get_columns()

        # Find which column was clicked
        for i, col in enumerate(columns):
            if col == column:
                # Get sort order
                order = column.get_sorter_order()

                # Clear existing sorters
                self.sorter.remove_all()

                # Add new sorter if actively sorting
                if order != Gtk.SorterOrder.NONE:
                    sorter = column.get_sorter()
                    if sorter:
                        self.sorter.append(sorter)

                # Log for debugging
                print(f"Column {i} ({column.get_title()}) clicked, order: {order}")
                break

    def _setup_text_cell(self, factory, list_item):
        """Setup a basic text cell."""
        label = Gtk.Label(xalign=0, margin_start=12, margin_end=12)
        list_item.set_child(label)

    def _bind_name_cell(self, factory, list_item):
        """Bind the kernel name cell."""
        kernel = list_item.get_item()
        label = list_item.get_child()
        label.set_text(kernel.get_property("name"))
        if kernel.get_property("running"):
            label.add_css_class("bold")
        else:
            label.remove_css_class("bold")

    def _bind_version_cell(self, factory, list_item):
        """Bind the version cell."""
        kernel = list_item.get_item()
        label = list_item.get_child()
        label.set_text(kernel.get_property("version"))

    def _setup_type_cell(self, factory, list_item):
        """Setup the type cell for LTS/RT badges."""
        box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=4,
            margin_start=12,
            margin_end=12,
        )
        list_item.set_child(box)

    def _bind_type_cell(self, factory, list_item):
        """Bind the type cell with LTS/RT badges."""
        kernel = list_item.get_item()
        box = list_item.get_child()

        # Clear previous children
        while box.get_first_child():
            box.remove(box.get_first_child())

        if kernel.get_property("is_lts"):
            box.append(self._create_badge("LTS", "success"))

        if kernel.get_property("is_rt"):
            box.append(self._create_badge("RT", "accent"))

    def _setup_action_cell(self, factory, list_item):
        """Setup the action button cell."""
        button = Gtk.Button(margin_start=12, margin_end=12)
        button.set_size_request(90, 30)

        # Make button more compact
        button_content = button.get_first_child()
        if button_content:
            button_content.set_margin_top(2)
            button_content.set_margin_bottom(2)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.append(button)
        list_item.set_child(box)

    def _bind_action_cell(self, factory, list_item):
        """Bind the action button cell."""
        kernel = list_item.get_item()
        box = list_item.get_child()
        button = box.get_first_child()
        button.kernel = kernel

        # Disconnect any existing signals
        for handler_id in getattr(button, "handler_ids", []):
            if button.handler_is_connected(handler_id):
                button.disconnect(handler_id)
        button.handler_ids = []

        # Setup button based on kernel status
        if kernel.get_property("running"):
            self._setup_running_button(button)
        elif kernel.get_property("installed"):
            self._setup_installed_button(button)
        else:
            self._setup_not_installed_button(button)

    def _setup_running_button(self, button):
        """Setup button for running kernel."""
        button.set_label("In Use")
        button.set_sensitive(False)
        button.add_css_class("warning")
        button.remove_css_class("destructive-action")
        button.remove_css_class("suggested-action")

    def _setup_installed_button(self, button):
        """Setup button for installed (but not running) kernel."""
        button.set_label("Remove")
        button.set_sensitive(True)
        button.add_css_class("destructive-action")
        button.remove_css_class("warning")
        button.remove_css_class("suggested-action")

        # Connect remove handler
        handler_id = button.connect("clicked", self._on_remove_clicked)
        button.handler_ids = [handler_id]

    def _setup_not_installed_button(self, button):
        """Setup button for not installed kernel."""
        button.set_label("Install")
        button.set_sensitive(True)
        button.add_css_class("suggested-action")
        button.remove_css_class("destructive-action")
        button.remove_css_class("warning")

        # Connect install handler
        handler_id = button.connect("clicked", self._on_install_clicked)
        button.handler_ids = [handler_id]

    def _show_loading_ui(self):
        """Show loading UI and hide kernel list."""
        # Remove existing loading page
        if self.loading_page:
            self.content.remove(self.loading_page)
            self.loading_page = None

        # Create new loading page
        self.loading_page = Adw.StatusPage(
            icon_name="emblem-synchronizing-symbolic",
            title="Loading Kernels",
            description="Please wait while we retrieve kernel information",
        )

        spinner = Gtk.Spinner()
        spinner.set_size_request(24, 24)
        spinner.start()
        self.loading_page.set_child(spinner)

        # Add to content and hide kernel list
        self.content.prepend(self.loading_page)
        self.kernel_list_box.set_visible(False)

    def _hide_loading_ui(self):
        """Hide the loading UI."""
        if self.loading_page:
            self.content.remove(self.loading_page)
            self.loading_page = None
        self.kernel_list_box.set_visible(True)

    def _load_kernels(self):
        """Load kernel information."""
        threading.Thread(target=self._background_load_kernels, daemon=True).start()
        return False

    def _background_load_kernels(self):
        """Load kernels in background thread."""
        try:
            kernels = self.kernel_manager.get_available_kernels()
            GLib.idle_add(self._display_kernels, kernels)
        except Exception as e:
            GLib.idle_add(self._show_error, str(e))

    def _display_kernels(self, kernels):
        """Display the kernel list in the UI."""
        # Hide loading UI and clear current model
        self._hide_loading_ui()
        self.store.remove_all()

        if not kernels:
            self._show_empty_state()
            return False

        # Add kernels directly to store - no need for sorting as it will be handled by GTK
        for kernel in kernels:
            self.store.append(KernelModel(kernel))

        return False

    def _show_empty_state(self):
        """Show message when no kernels are available."""
        # Hide kernel list
        self.kernel_list_box.set_visible(False)

        # Create empty state if it doesn't exist
        if not hasattr(self, "empty_state"):
            self.empty_state = Adw.StatusPage(
                icon_name="dialog-warning-symbolic",
                title="No Kernel Versions Available",
                description="Check your internet connection and try again",
            )

            button = Gtk.Button(label="Retry", css_classes=["pill", "suggested-action"])
            button.connect("clicked", lambda _: self._refresh_kernels())
            self.empty_state.set_child(button)

        # Add to content
        if self.empty_state not in self.content:
            self.content.append(self.empty_state)

    def _show_error(self, error_message):
        """Show error message when kernel loading fails."""
        # Hide loading UI and kernel list
        self._hide_loading_ui()
        self.kernel_list_box.set_visible(False)

        # Create or update error state
        if not hasattr(self, "error_state"):
            self.error_state = Adw.StatusPage(
                icon_name="dialog-error-symbolic",
                title="Error Loading Kernels",
                description=error_message,
            )

            button = Gtk.Button(label="Retry", css_classes=["pill", "suggested-action"])
            button.connect("clicked", lambda _: self._refresh_kernels())
            self.error_state.set_child(button)
        else:
            self.error_state.set_description(error_message)

        # Add to content
        if self.error_state not in self.content:
            self.content.append(self.error_state)

        return False

    def _refresh_kernels(self):
        """Refresh kernel list."""
        # Hide any status pages
        if hasattr(self, "empty_state") and self.empty_state in self.content:
            self.content.remove(self.empty_state)

        if hasattr(self, "error_state") and self.error_state in self.content:
            self.content.remove(self.error_state)

        self._show_loading_ui()
        GLib.timeout_add(100, self._load_kernels)

    def _create_badge(self, text, style_class):
        """Create a styled badge widget."""
        badge = Gtk.Label(label=text)
        badge.add_css_class("caption")
        badge.add_css_class("tag")
        badge.add_css_class(style_class)
        return badge

    def _on_install_clicked(self, button):
        """Handle install button click."""
        kernel = button.kernel
        self._show_confirmation_dialog(
            title="Install Kernel",
            message=(
                f"Are you sure you want to install the {kernel.get_property('name')} kernel?\n\n"
                "This will install the kernel and its modules.\n"
                "This operation requires sudo privileges."
            ),
            action="install",
            kernel=kernel.original_data,
            button=button,
        )

    def _on_remove_clicked(self, button):
        """Handle remove button click."""
        kernel = button.kernel
        self._show_confirmation_dialog(
            title="Remove Kernel",
            message=(
                f"Are you sure you want to remove the {kernel.get_property('name')} kernel?\n\n"
                "This will remove the kernel and its modules.\n"
                "This operation requires sudo privileges."
            ),
            action="remove",
            kernel=kernel.original_data,
            button=button,
            destructive=True,
        )

    def _show_confirmation_dialog(
        self, title, message, action, kernel, button, destructive=False
    ):
        """Show confirmation dialog for kernel operations."""
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading(title)
        dialog.set_body(message)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response(action, "Yes, " + action.title())

        dialog.set_response_appearance(
            action,
            Adw.ResponseAppearance.DESTRUCTIVE
            if destructive
            else Adw.ResponseAppearance.SUGGESTED,
        )
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        # Connect response handler
        dialog.connect(
            "response",
            lambda d, r: self._on_dialog_response(d, r, action, kernel, button),
        )

        dialog.present()

    def _on_dialog_response(self, dialog, response, action, kernel, button):
        """Handle dialog response for both install and remove actions."""
        if response != action:
            return

        # Setup progress dialog
        progress_dialog = ProgressDialog(
            parent_window=self.get_root(),
            title=f"{action.title()}ing {kernel['name']} Kernel",
            operation_type=action,
            target_name=kernel["name"],
            cancel_callback=lambda: self._on_operation_canceled(kernel),
        )

        # Store reference and show dialog
        self.progress_dialog = progress_dialog
        progress_dialog.show()

        # Disable button and show initial message
        button.set_sensitive(False)
        progress_dialog.append_terminal_text(
            f"Starting {action} of {kernel['name']} kernel...\n"
            f"This may take a few minutes. Please wait...\n"
        )

        # Start operation in background
        operation_method = (
            self.kernel_manager.install_kernel
            if action == "install"
            else self.kernel_manager.remove_kernel
        )

        operation_method(
            kernel,
            progress_callback=progress_dialog.update_progress,
            output_callback=progress_dialog.append_terminal_text,
            complete_callback=lambda success: GLib.idle_add(
                self._operation_complete, button, kernel, action, success
            ),
        )

    def _on_operation_canceled(self, kernel):
        """Handle cancel button click during operation."""
        if hasattr(self, "progress_dialog"):
            delattr(self, "progress_dialog")
        self._load_kernels()

    def _operation_complete(self, button, kernel, operation, success):
        """Handle operation completion."""
        # Re-enable button
        button.set_sensitive(True)

        # Update progress dialog
        if hasattr(self, "progress_dialog") and self.progress_dialog:
            self.progress_dialog.set_complete(success)

        # Show toast notification
        operation_name = "installation" if operation == "install" else "removal"
        message = f"Kernel {operation_name} {'successful' if success else 'failed'}"
        self._show_toast(message, "error" if not success else "success")

        # Refresh kernel list
        self._refresh_kernels()
        return False

    def _show_toast(self, message, style="success"):
        """Show a toast notification."""
        window = self.get_root()
        if window and hasattr(window, "add_toast"):
            window.add_toast(message)
            return

        # Fallback to looking for toast overlay
        overlay = self._find_toast_overlay()
        if overlay:
            toast = Adw.Toast.new(message)
            toast.set_timeout(3)
            if style == "error":
                toast.set_priority(Adw.ToastPriority.HIGH)
            overlay.add_toast(toast)

    def _find_toast_overlay(self):
        """Find the nearest ToastOverlay in the widget hierarchy."""
        widget = self
        while widget:
            if isinstance(widget, Adw.ToastOverlay):
                return widget

            parent = widget.get_parent()
            if parent is None:
                # Try to get the root
                root = widget.get_root()
                if root and hasattr(root, "get_content"):
                    content = root.get_content()
                    if isinstance(content, Adw.ToastOverlay):
                        return content
                break

            widget = parent

        return None
