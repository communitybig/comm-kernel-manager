#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Kernel Management Page

This module defines the UI for kernel management, allowing users
to install and manage different kernel versions.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from core.kernel_manager import KernelManager


class KernelPage(Gtk.Box):
    """Page for kernel management."""

    def __init__(self):
        """Initialize the kernel management page."""
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(24)
        self.set_margin_bottom(24)
        self.set_margin_start(24)
        self.set_margin_end(24)
        
        # Initialize kernel manager
        self.kernel_manager = KernelManager()
        
        # Create content
        self._create_content()
        
        # Load available kernels
        self._load_kernels()
    
    def _create_content(self):
        """Create the UI elements for kernel management with fixed layout."""
        # Create main container as scrolled window to maintain fixed window size
        main_scrolled = Gtk.ScrolledWindow()
        main_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_scrolled.set_min_content_height(580)  # Adjust to match your window height
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
        
        # Add header with Adw.PreferencesGroup for better GNOME style
        kernel_group = Adw.PreferencesGroup()
        kernel_group.set_title("Kernel Versions")
        kernel_group.set_description("Select a kernel version to install or update")
        
        # Create scrolled window for kernels that will resize itself
        self.kernels_scrolled = Gtk.ScrolledWindow()
        self.kernels_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.kernels_scrolled.set_vexpand(True)
        # Important: Start with a larger height, will shrink when progress appears
        self.kernels_scrolled.set_min_content_height(450)
        
        # Create listbox for kernels with GNOME styling
        self.kernel_listbox = Gtk.ListBox()
        self.kernel_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.kernel_listbox.add_css_class("boxed-list")
        self.kernel_listbox.add_css_class("card")
        
        self.kernels_scrolled.set_child(self.kernel_listbox)
        kernel_group.add(self.kernels_scrolled)
        
        # Add the group to the content box
        content_box.append(kernel_group)
        
        # Progress section (initially hidden)
        progress_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        progress_card.add_css_class("card")
        progress_card.set_margin_top(16)
        progress_card.set_spacing(8)
        
        self.progress_label = Gtk.Label.new("Installation Progress")
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
        
        # Terminal expander
        terminal_expander = Gtk.Expander()
        terminal_expander.set_label("Show Terminal Output")
        terminal_expander.add_css_class("caption")
        terminal_expander.set_margin_top(8)
        terminal_expander.set_margin_start(16)
        terminal_expander.set_margin_end(16)
        terminal_expander.set_margin_bottom(8)
        self.terminal_expander = terminal_expander
        
        # Create scrolled terminal - doesn't expand the window
        terminal_scroll = Gtk.ScrolledWindow()
        terminal_scroll.set_min_content_height(150)
        terminal_scroll.set_max_content_height(150)
        terminal_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        terminal_scroll.set_vexpand(False)
        
        # Create terminal view
        self.terminal_view = Gtk.TextView()
        self.terminal_view.set_editable(False)
        self.terminal_view.set_cursor_visible(False)
        self.terminal_view.set_monospace(True)
        self.terminal_view.add_css_class("terminal")
        self.terminal_view.add_css_class("monospace")
        self.terminal_view.add_css_class("card")
        self.terminal_buffer = self.terminal_view.get_buffer()
        
        terminal_scroll.set_child(self.terminal_view)
        terminal_expander.set_child(terminal_scroll)
        
        # Connect signal for terminal expansion
        terminal_expander.connect("notify::expanded", self._on_terminal_expanded)
        
        progress_card.append(terminal_expander)
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
        
    def _on_terminal_expanded(self, expander, param):
        """Adjust layout when terminal is expanded/collapsed."""
        expanded = expander.get_expanded()
        
        if expanded:
            # When terminal is expanded, reduce the kernel list height
            self.kernels_scrolled.set_min_content_height(250)
        else:
            # When terminal is collapsed, restore kernel list height
            self.kernels_scrolled.set_min_content_height(350)

    def _show_progress_container(self):
        """Show the progress container and adjust layout."""
        if not self.progress_container.get_visible():
            self.progress_container.set_visible(True)
            # Reduce the kernel list size when progress container appears
            self.kernels_scrolled.set_min_content_height(350)
            
    def _hide_progress_container(self):
        """Hide the progress container and restore layout."""
        if hasattr(self, 'terminal_expander'):
            self.terminal_expander.set_expanded(False)
        
        # Reset terminal buffer
        if hasattr(self, 'terminal_buffer') and self.terminal_buffer:
            self.terminal_buffer.set_text("", 0)
        
        # Delay hiding to let animations complete
        GLib.timeout_add(100, self._actually_hide_progress_container)
        return False
    
    def _actually_hide_progress_container(self):
        """Actually hide the progress container."""
        self.progress_container.set_visible(False)
        # Restore the kernel list to full size
        self.kernels_scrolled.set_min_content_height(450)
        return False
        
    def _load_kernels(self):
        """Load available kernels from the kernel manager."""
        # Clear existing items
        while True:
            row = self.kernel_listbox.get_first_child()
            if row is None:
                break
            self.kernel_listbox.remove(row)
        
        # Get available kernels
        kernels = self.kernel_manager.get_available_kernels()
        
        # Add kernels to the list
        for kernel in kernels:
            row = self._create_kernel_row(kernel)
            self.kernel_listbox.append(row)
    
    def _create_kernel_row(self, kernel):
        """
        Create a row for a kernel in the list.
        
        Args:
            kernel: Dictionary with kernel information.
            
        Returns:
            Gtk.ListBoxRow: The created row.
        """
        # Create a row with kernel information
        row = Adw.ActionRow()
        row.set_title(kernel["name"])
        row.set_subtitle(f"Version: {kernel['version']}")
        
        # Add kernel icon (using a more specific icon based on kernel type)
        icon_name = "system-run-symbolic"
        if kernel.get("xanmod", False):
            icon_name = "application-x-executable-symbolic"
        elif "lts" in kernel["name"].lower() or kernel.get("lts", False):
            icon_name = "emblem-default-symbolic"
            
        icon = Gtk.Image.new_from_icon_name(icon_name)
        row.add_prefix(icon)
        
        # Container for kernel tags on the left
        tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tag_box.set_margin_end(12)
        
        # Add tag for RT kernels if applicable
        if "rt" in kernel.get("name", "") or kernel.get("rt", False):
            rt_tag = Gtk.Label.new("RT")
            rt_tag.add_css_class("accent")
            rt_tag.add_css_class("tag")
            rt_tag.add_css_class("caption")
            rt_tag.set_margin_start(4)
            rt_tag.set_margin_end(4)
            rt_box = Gtk.Box()
            rt_box.add_css_class("card")
            rt_box.add_css_class("accent")
            rt_box.set_margin_end(4)
            rt_box.append(rt_tag)
            tag_box.append(rt_box)
        
        # Add tag for LTS kernels
        if "-lts" in kernel.get("name", "") or kernel.get("lts", False):
            lts_tag = Gtk.Label.new("LTS")
            lts_tag.add_css_class("success")
            lts_tag.add_css_class("tag")
            lts_tag.add_css_class("caption")
            lts_tag.set_margin_start(4)
            lts_tag.set_margin_end(4)
            lts_box = Gtk.Box()
            lts_box.add_css_class("card")
            lts_box.add_css_class("success")
            lts_box.set_margin_end(4)
            lts_box.append(lts_tag)
            tag_box.append(lts_box)
        
        # Add tag for optimized builds
        if kernel.get("optimized", False):
            opt_tag = Gtk.Label.new(f"x64v{kernel.get('opt_level', '')}")
            opt_tag.add_css_class("accent")
            opt_tag.add_css_class("tag")
            opt_tag.add_css_class("caption")
            opt_tag.set_margin_start(4)
            opt_tag.set_margin_end(4)
            opt_box = Gtk.Box()
            opt_box.add_css_class("card")
            opt_box.add_css_class("accent")
            opt_box.set_margin_end(4)
            opt_box.append(opt_tag)
            tag_box.append(opt_box)
            
        # Add tags to the row if any were created
        if tag_box.get_first_child() is not None:
            row.add_suffix(tag_box)
        
        # Add buttons in a button box for better alignment
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_margin_top(8)
        button_box.set_margin_bottom(8)
        
        if kernel.get("installed", False):
            # If kernel is already installed, show the "Installed" tag and offer removal
            installed_tag = Gtk.Label.new("Installed")
            installed_tag.add_css_class("success")
            installed_tag.add_css_class("caption")
            installed_tag.set_margin_start(4)
            installed_tag.set_margin_end(4)
            
            installed_box = Gtk.Box()
            installed_box.add_css_class("card")
            installed_box.add_css_class("success")
            installed_box.set_margin_start(4)
            installed_box.set_margin_end(8)
            installed_box.append(installed_tag)
            button_box.append(installed_box)
            
            # Only offer removal if it's not the currently running kernel
            remove_button = Gtk.Button.new_with_label("Remove")
            remove_button.add_css_class("destructive-action")
            remove_button.connect("clicked", self._on_remove_clicked, kernel)
            button_box.append(remove_button)
        else:
            # Add install button for non-installed kernels
            install_button = Gtk.Button.new_with_label("Install")
            install_button.add_css_class("suggested-action")
            install_button.connect("clicked", self._on_install_clicked, kernel)
            button_box.append(install_button)
        
        row.add_suffix(button_box)
        
        # Add some extra whitespace for better readability
        row.set_margin_top(2)
        row.set_margin_bottom(2)
            
        return row
    
    def _on_refresh_clicked(self, button):
        """Callback for refresh button click."""
        self._load_kernels()
    
    def _on_install_clicked(self, button, kernel):
        """Callback for install button click."""
        # Show confirmation dialog
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading("Install Kernel")
        dialog.set_body(f"Are you sure you want to install the {kernel['name']} kernel?\n\nThis will install the kernel and its modules.\nThis operation requires sudo privileges.")
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        # Connect response signal
        dialog.connect("response", self._on_install_dialog_response, kernel, button)
        
        dialog.present()

    def _on_install_dialog_response(self, dialog, response, kernel, button):
        """Handle install dialog response."""
        if response != "install":
            return
        
        # Show progress immediately
        self._show_progress_container()
        self.progress_label.set_text(f"Installing {kernel['name']} Kernel")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text(f"Preparing to install {kernel['name']}...")
        
        # Clear terminal buffer
        if hasattr(self, 'terminal_buffer') and self.terminal_buffer:
            self.terminal_buffer.set_text("", 0)
        
        # Disable button
        button.set_sensitive(False)
        
        # Add initial terminal output
        self._direct_terminal_output(f"Starting installation of {kernel['name']} kernel...\n")
        self._direct_terminal_output(f"This may take a few minutes. Please wait...\n")
        
        # Start installation
        self.kernel_manager.install_kernel(
            kernel,
            progress_callback=self._update_progress,
            output_callback=self._output_to_terminal,
            complete_callback=lambda success: GLib.idle_add(
                self._installation_complete, button, success
            )
        )
    
    def _on_remove_clicked(self, button, kernel):
        """
        Callback for remove button click.
        
        Args:
            button: The button that was clicked.
            kernel: The kernel to remove.
        """
        # Show confirmation dialog before removing - compatible with older libadwaita
        dialog = Adw.MessageDialog.new(self.get_root())
        dialog.set_heading("Remove Kernel")
        dialog.set_body(f"Are you sure you want to remove the {kernel['name']} kernel?\n\nThis will remove the kernel and its modules.\nThis operation requires sudo privileges.")
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        # Connect the response signal
        dialog.connect("response", self._on_remove_dialog_response, kernel, button)
        
        # Show the dialog
        dialog.present()

    def _on_remove_dialog_response(self, dialog, response, kernel, button):
        """Handle the remove confirmation dialog response."""
        if response != "remove":
            return
        
        # Imediatamente mostrar progresso
        self.progress_container.set_visible(True)
        self.progress_label.set_text(f"Removing {kernel['name']} Kernel")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text(f"Preparing to remove {kernel['name']}...")
        
        # Limpar o buffer de terminal antes de iniciar
        if hasattr(self, 'terminal_buffer') and self.terminal_buffer:
            self.terminal_buffer.set_text("", 0)
        
        # Disable button during removal
        button.set_sensitive(False)
        
        # Adicionar mensagem ao terminal diretamente para feedback ao usuário
        self._direct_terminal_output(f"Starting removal of {kernel['name']} kernel...\n")
        self._direct_terminal_output(f"This may take a few minutes. Please wait...\n")
        
        # Start removal in a separate thread to avoid UI freezing
        self.kernel_manager.remove_kernel(
            kernel,
            progress_callback=self._update_progress,
            output_callback=self._output_to_terminal,
            complete_callback=lambda success: GLib.idle_add(
                self._removal_complete, button, success
            )
        )
    
    def _update_progress(self, fraction, text=None):
        """
        Update the progress bar.
        
        Args:
            fraction: Progress fraction (0.0 to 1.0).
            text: Optional text to display.
        """
        # Utilize GLib.idle_add para garantir que as atualizações ocorram no thread principal
        GLib.idle_add(self._update_progress_idle, fraction, text)

    def _update_progress_idle(self, fraction, text):
        """Update progress bar from main thread."""
        # Limitar a fração entre 0 e 1
        fraction = max(0.0, min(1.0, fraction))
        
        # Atualizar a barra de progresso
        self.progress_bar.set_fraction(fraction)
        
        # Atualizar o texto, incluindo a porcentagem
        if text:
            # Adicionar porcentagem ao texto se não estiver presente
            if "%" not in text:
                percentage = fraction * 100
                display_text = f"{text} ({percentage:.1f}%)"
            else:
                display_text = text
            
            self.progress_bar.set_text(display_text)
            self.progress_label.set_text(display_text)
        else:
            # Apenas exibir a porcentagem se nenhum texto for fornecido
            percentage = fraction * 100
            display_text = f"Progress: {percentage:.1f}%"
            self.progress_bar.set_text(display_text)
        
        # Garantir que a barra de progresso esteja visível
        if not self.progress_container.get_visible():
            self.progress_container.set_visible(True)
            
        return False  # Não chamar novamente
    
    def _direct_terminal_output(self, text):
        """
        Add text directly to the terminal buffer without using threads or idle_add.
        This method should only be called from the main thread.
        """
        if not hasattr(self, 'terminal_buffer') or not self.terminal_buffer:
            return
            
        end_iter = self.terminal_buffer.get_end_iter()
        self.terminal_buffer.insert(end_iter, text)
        
        # Rolar para o final
        vadj = self.terminal_view.get_vadjustment()
        if vadj:
            vadj.set_value(vadj.get_upper() - vadj.get_page_size())
    
    def _output_to_terminal(self, text):
        """
        Add text to the terminal view.
        
        Args:
            text: Text to add to the terminal.
        """
        if not text:
            return
            
        # Add newline if needed
        if not text.endswith('\n'):
            text += '\n'
        
        # Use GLib.idle_add para garantir que a manipulação do buffer ocorra no thread principal
        GLib.idle_add(self._output_to_terminal_idle, text)

    def _output_to_terminal_idle(self, text):
        """
        Add text to the terminal view from the main thread.
        
        Args:
            text: Text to add to the terminal.
        """
        try:
            if not hasattr(self, 'terminal_buffer') or not self.terminal_buffer:
                print(f"Terminal output (no buffer): {text.strip()}")
                return False
                
            # Obter o buffer do TextView
            buffer = self.terminal_buffer
            
            # No GTK 4, devemos sempre obter um novo iterador do final
            end_iter = buffer.get_end_iter()
            
            # Inserir texto no final
            buffer.insert(end_iter, text)
            
            # Rolar para o final - método seguro para GTK 4
            # Primeiro obter o ajuste vertical
            vadj = self.terminal_view.get_vadjustment()
            if vadj:
                # Rolar para a posição máxima
                vadj.set_value(vadj.get_upper() - vadj.get_page_size())
            
            # Log também no console por segurança
            print(f"Terminal output: {text.strip()}")
        except Exception as e:
            print(f"Error updating terminal: {e}")
        
        return False  # Não chamar novamente
    
    def _installation_complete(self, button, success):
        """Handle installation completion."""
        # Re-enable button
        button.set_sensitive(True)
        
        # Update progress
        if success:
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("Installation complete!")
            
            # Show completion dialog
            self._show_completion_dialog(
                "Installation Complete", 
                f"The kernel was installed successfully.\nYou may need to reboot to use the new kernel.",
                "success"
            )
        else:
            self.progress_bar.set_text("Installation failed.")
            
            # Show failure dialog
            self._show_completion_dialog(
                "Installation Failed", 
                "The kernel installation failed. Please check the terminal output for details.",
                "error"
            )
        
        # Refresh kernel list
        self._load_kernels()
        
        return False

    def _removal_complete(self, button, success):
        """Handle removal completion."""
        # Re-enable button
        button.set_sensitive(True)
        
        # Update progress
        if success:
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text("Removal complete!")
            
            # Show completion dialog
            self._show_completion_dialog(
                "Removal Complete", 
                "The kernel was removed successfully.",
                "success"
            )
        else:
            self.progress_bar.set_text("Removal failed.")
            
            # Show failure dialog
            self._show_completion_dialog(
                "Removal Failed", 
                "The kernel removal failed. Please check the terminal output for details.",
                "error"
            )
        
        # Refresh kernel list
        self._load_kernels()
        
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
        # Ensure the terminal is contracted before hiding
        if hasattr(self, 'terminal_expander'):
            self.terminal_expander.set_expanded(False)
        
        # Reset terminal buffer to avoid unnecessary scrollbars
        if hasattr(self, 'terminal_buffer') and self.terminal_buffer:
            self.terminal_buffer.set_text("", 0)
        
        # Small delay before hiding to ensure animations are complete
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