#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Mesa Manager

This module provides functionality for managing Mesa drivers
including listing, installing, and switching between different versions.
"""

import os
import re
import subprocess
import threading
import time
from core.package_manager import PackageManager


class MesaManager:
    """Manager for handling Mesa drivers."""

    def __init__(self):
        """Initialize the Mesa manager."""
        self.package_manager = PackageManager()
        
        # Define available Mesa drivers
        self._define_available_drivers()
    
    def _define_available_drivers(self):
        """Define available Mesa driver options."""
        self.drivers = [
            {
                "id": "amber",
                "name": "Amber",
                "packages": ["mesa-amber"],
                "conflicts": ["mesa", "mesa-git", "mesa-tkg-git"],
                "description": "Stable and well-tested version of Mesa"
            },
            {
                "id": "stable",
                "name": "Stable",
                "packages": ["mesa"],
                "conflicts": ["mesa-amber", "mesa-git", "mesa-tkg-git"],
                "description": "Regular Mesa release"
            },
            {
                "id": "tkg-stable",
                "name": "Tkg-Stable",
                "packages": ["mesa-tkg"],
                "conflicts": ["mesa", "mesa-amber", "mesa-git", "mesa-tkg-git"],
                "description": "Enhanced performance build of stable Mesa"
            },
            {
                "id": "tkg-git",
                "name": "Tkg-git",
                "packages": ["mesa-tkg-git"],
                "conflicts": ["mesa", "mesa-amber", "mesa-tkg"],
                "description": "Latest development version with cutting-edge features"
            }
        ]
    
    def get_available_drivers(self):
        """
        Get a list of available Mesa drivers.
        
        Returns:
            list: List of available Mesa drivers with their information.
        """
        # Determine which driver is currently active
        active_driver = self._get_active_driver()
        
        # Mark the active driver
        drivers = self.drivers.copy()
        for driver in drivers:
            driver["active"] = (driver["id"] == active_driver)
        
        return drivers
    
    def _get_active_driver(self):
        """
        Determine which Mesa driver is currently active.
        
        Returns:
            str: ID of the active driver, or None if not determined.
        """
        # Get installed Mesa packages
        installed_packages = self.package_manager.get_installed_packages()
        installed_names = [pkg["name"] for pkg in installed_packages]
        
        # Check each driver
        for driver in self.drivers:
            # If any of the driver's packages are installed, consider it active
            for package in driver["packages"]:
                if package in installed_names:
                    return driver["id"]
        
        # Default to stable if no specific driver is detected
        return "stable"
    
    def apply_driver(self, driver_id, progress_callback=None, complete_callback=None):
        """
        Apply a Mesa driver configuration.
        
        Args:
            driver_id: ID of the driver to apply.
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        # Find the driver by ID
        selected_driver = None
        for driver in self.drivers:
            if driver["id"] == driver_id:
                selected_driver = driver
                break
        
        if not selected_driver:
            if complete_callback:
                complete_callback(False)
            return
        
        # Start a thread for applying the driver
        threading.Thread(
            target=self._apply_driver_thread,
            args=(selected_driver, progress_callback, complete_callback),
            daemon=True
        ).start()
    
    def _apply_driver_thread(self, driver, progress_callback, complete_callback):
        """
        Thread function for applying a driver.
        
        Args:
            driver: The driver configuration to apply.
            progress_callback: Callback function for progress updates.
            complete_callback: Callback function for completion notification.
        """
        if progress_callback:
            progress_callback(0.1, f"Applying {driver['name']} driver...")
        
        try:
            # 1. First, remove conflicting packages
            if driver["conflicts"]:
                if progress_callback:
                    progress_callback(0.2, "Removing conflicting packages...")
                
                # Build remove command
                remove_cmd = [
                    self.package_manager.sudo_command,
                    "pacman",
                    "-Rs",
                    "--noconfirm"
                ]
                
                # Add conflicts to remove
                installed_conflicts = []
                for conflict in driver["conflicts"]:
                    if self.package_manager.is_package_installed(conflict):
                        installed_conflicts.append(conflict)
                
                # If there are conflicts to remove
                if installed_conflicts:
                    remove_cmd.extend(installed_conflicts)
                    
                    # Execute remove command
                    remove_process = subprocess.Popen(
                        remove_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        bufsize=1
                    )
                    
                    # Process output
                    for line in iter(remove_process.stdout.readline, ""):
                        if "removing" in line.lower():
                            if progress_callback:
                                progress_callback(0.3, "Removing conflicting packages...")
                    
                    # Wait for completion
                    remove_process.wait()
                    
                    # Check if successful
                    if remove_process.returncode != 0:
                        if progress_callback:
                            progress_callback(0.0, "Failed to remove conflicting packages.")
                        
                        if complete_callback:
                            complete_callback(False)
                        return
            
            # 2. Install the new packages
            if progress_callback:
                progress_callback(0.4, f"Installing {driver['name']} packages...")
            
            # Build install command
            install_cmd = [
                self.package_manager.sudo_command,
                "pacman",
                "-S",
                "--noconfirm"
            ]
            install_cmd.extend(driver["packages"])
            
            # Execute install command
            install_process = subprocess.Popen(
                install_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Initialize progress tracking variables
            downloading = False
            installing = False
            progress = 0.4
            
            # Process output
            for line in iter(install_process.stdout.readline, ""):
                # Parse progress information
                if "Downloading" in line and "%" in line:
                    downloading = True
                    # Extract download percentage if possible
                    match = re.search(r"\((\d+)/(\d+)\)", line)
                    if match:
                        current = int(match.group(1))
                        total = int(match.group(2))
                        progress = 0.4 + (current / total) * 0.3  # 40%-70% for downloading
                        
                        if progress_callback:
                            progress_callback(progress, f"Downloading packages ({current}/{total})...")
                
                elif "Installing" in line:
                    installing = True
                    if progress_callback:
                        progress_callback(0.7, "Installing packages...")
                
                elif installing and "installing" in line.lower():
                    # Rough estimation of installation progress
                    progress = min(0.7 + progress * 0.1, 0.9)  # 70%-90% for installing
                    if progress_callback:
                        progress_callback(progress, "Installing...")
            
            # Wait for completion
            install_process.wait()
            
            # Check if successful
            if install_process.returncode != 0:
                if progress_callback:
                    progress_callback(0.0, "Failed to install packages.")
                
                if complete_callback:
                    complete_callback(False)
                return
            
            # Final progress update
            if progress_callback:
                progress_callback(1.0, "Driver applied successfully!")
            
            # Notify completion
            if complete_callback:
                complete_callback(True)
                
        except Exception as e:
            # Handle exceptions
            if progress_callback:
                progress_callback(0.0, f"Error: {str(e)}")
            
            if complete_callback:
                complete_callback(False)