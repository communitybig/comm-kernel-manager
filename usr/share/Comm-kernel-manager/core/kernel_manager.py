#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kernel Manager Application - Kernel Manager

This module provides functionality for managing Linux kernels
including listing, installing, and removing kernels.
"""

import os
import re
import subprocess
import threading
import logging
import time
import requests
from xml.etree import ElementTree
from core.package_manager import PackageManager


class KernelManager:
    """Manager for handling Linux kernels."""

    def __init__(self):
        """Initialize the kernel manager."""
        self.package_manager = PackageManager()

        # Define true kernel patterns (not modules)
        self.kernel_patterns = [
            r"^linux\d*$",  # Standard kernels (linux, linux59, etc.)
            r"^linux-lts$",  # Long term support kernel
            r"^linux\d*-lts$",  # LTS kernels with version number
            r"^linux-hardened$",  # Hardened kernel
            r"^linux-zen$",  # Zen kernel
            r"^linux-xanmod$",  # Xanmod kernel
            r"^linux\d*-xanmod$",  # Xanmod kernels with version number
            r"^linux-xanmod-lts$",  # Xanmod LTS kernel
            r"^linux\d*-xanmod-lts$",  # Xanmod LTS kernels with version number
            r"^linux\d*-rt$",  # Real-time kernels
            r"^linux-xanmod-x64v\d$",  # Xanmod optimized builds
            r"^linux-xanmod-lts-x64v\d$",  # Xanmod LTS optimized builds
        ]

        # Excluded patterns (modules and other non-kernel packages)
        self.excluded_patterns = [
            r"-acpi_call",
            r"-bbswitch",
            r"-broadcom",
            r"-headers",
            r"-ndiswrapper",
            r"-nvidia",
            r"-r8168",
            r"-virtualbox",
            r"-zfs",
            r"-tp_smapi",
            r"-vhba-module",
            r"-rtl8723bu",
        ]

        # Get LTS kernel versions from kernel.org
        self.lts_versions = self._get_lts_kernel_versions()

    def _get_lts_kernel_versions(self):
        """
        Get a list of current LTS kernel versions from kernel.org.

        Returns:
            list: List of LTS kernel versions as strings (e.g. "612" for 6.12).
        """
        lts_versions = []
        try:
            # Fetch kernel.org feed
            response = requests.get("https://www.kernel.org/feeds/kdist.xml", timeout=5)
            if response.status_code == 200:
                # Parse XML
                root = ElementTree.fromstring(response.content)
                # Find all entries with "longterm" in title
                for item in root.findall(".//item"):
                    title = item.find("title")
                    if title is not None and ": longterm" in title.text:
                        # Extract version number
                        version_match = re.match(r"(\d+\.\d+).*: longterm", title.text)
                        if version_match:
                            version = version_match.group(1)
                            # Convert to format like "612" for 6.12
                            numeric_version = version.replace(".", "")
                            lts_versions.append(numeric_version)

            return lts_versions
        except Exception as e:
            logging.warning(f"Failed to get LTS kernel versions: {str(e)}")
            # Return a few known LTS versions as fallback
            return ["66", "612", "614"]

    def get_installed_kernels(self):
        """
        Get a list of installed kernels.

        Returns:
            list: List of installed kernels with their information.
        """
        installed_packages = self.package_manager.get_installed_packages()

        # Filter for kernel packages
        kernels = []
        for package in installed_packages:
            if self._is_kernel_package(package["name"]):
                kernel = {
                    "name": package["name"],
                    "version": package["version"],
                    "installed": True,
                }

                # Add kernel type flags
                self._add_kernel_flags(kernel)

                kernels.append(kernel)

        return kernels

    def get_available_kernels(self):
        """
        Get a list of available kernels from repositories.

        Returns:
            list: List of available kernels with their information.
        """
        # Get all available kernels
        available_kernels = []

        # Check each kernel pattern
        for pattern in self.kernel_patterns:
            # Get packages matching this pattern
            packages = self._search_kernel_packages(pattern)
            available_kernels.extend(packages)

        # Get installed kernels to mark them
        installed_kernels = self.get_installed_kernels()
        installed_names = [k["name"] for k in installed_kernels]

        # Filter out duplicates and excluded patterns
        filtered_kernels = []
        seen_kernels = set()

        for kernel in available_kernels:
            kernel_name = kernel["name"]

            # Skip if this is an excluded pattern (module package)
            if any(
                re.search(exclude, kernel_name) for exclude in self.excluded_patterns
            ):
                continue

            # Skip if we've already seen this kernel with the same version
            kernel_key = f"{kernel_name}-{kernel['version']}"
            if kernel_key in seen_kernels:
                continue

            seen_kernels.add(kernel_key)

            # Mark installed kernels
            kernel["installed"] = kernel_name in installed_names

            # Add kernel type flags
            self._add_kernel_flags(kernel)

            filtered_kernels.append(kernel)

        # Sort kernels by name and version
        return sorted(filtered_kernels, key=lambda k: (k["name"], k["version"]))

    def _search_kernel_packages(self, pattern):
        """
        Search for kernel packages matching a pattern.

        Args:
            pattern: Regex pattern to search for.

        Returns:
            list: List of matching packages.
        """
        # Use pacman to search for packages
        cmd = ["pacman", "-Ss", f"^{pattern}"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            return []

        packages = []
        current_package = None

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            # New package entry starts with repo/name version
            if line.startswith(" "):
                # This is a description line, skip
                continue

            # Parse package information
            match = re.match(r"([^\s]+)/([^\s]+)\s+([^\s]+)", line)
            if match:
                repo = match.group(1)
                package_name = match.group(2)
                package_version = match.group(3)

                # Only include if it's actually a kernel package
                if self._is_kernel_package(package_name):
                    packages.append({
                        "name": package_name,
                        "version": package_version,
                        "repository": repo,
                    })

        return packages

    def _is_kernel_package(self, package_name):
        """
        Check if a package is a true kernel package (not a module).

        Args:
            package_name: Name of the package.

        Returns:
            bool: True if it's a kernel package, False otherwise.
        """
        # Check if it matches any kernel pattern
        is_kernel = any(
            re.match(pattern, package_name) for pattern in self.kernel_patterns
        )

        # Ensure it's not an excluded pattern
        is_excluded = any(
            re.search(exclude, package_name) for exclude in self.excluded_patterns
        )

        return is_kernel and not is_excluded

    def _add_kernel_flags(self, kernel):
        """
        Add flags to identify kernel types (RT, LTS, etc.)

        Args:
            kernel: Kernel dictionary to update with flags.

        Returns:
            None: Updates the kernel dictionary in place.
        """
        kernel_name = kernel["name"]

        # Add RT flag
        if "-rt" in kernel_name:
            kernel["rt"] = True

        # Add LTS flag for explicitly named LTS kernels
        if "-lts" in kernel_name:
            kernel["lts"] = True

        # Check for Manjaro kernels that match LTS versions
        elif not "xanmod" in kernel_name and re.match(r"^linux\d+$", kernel_name):
            # Extract the version number from the kernel name
            version_match = re.match(r"^linux(\d+)$", kernel_name)
            if version_match:
                kernel_version = version_match.group(1)
                # Check if this version is in our LTS list
                if kernel_version in self.lts_versions:
                    kernel["lts"] = True

        # Add XanMod flag
        if "xanmod" in kernel_name:
            kernel["xanmod"] = True

        # Add optimized build flags (x64v3, x64v4)
        match = re.search(r"-x64v(\d)", kernel_name)
        if match:
            kernel["optimized"] = True
            kernel["opt_level"] = match.group(1)

    def _get_kernel_modules(self, kernel_name):
        """
        Get a list of module packages that should be installed with the kernel.

        Args:
            kernel_name: Name of the kernel.

        Returns:
            list: List of module package names.
        """
        # Standard modules to install with the kernel
        modules = [
            f"{kernel_name}-headers"  # Headers are always needed
        ]

        return modules

    def install_kernel(
        self,
        kernel,
        progress_callback=None,
        output_callback=None,
        complete_callback=None,
    ):
        """
        Install a kernel and its associated modules.

        Args:
            kernel: The kernel to install (dict with at least "name").
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        # Get the kernel name and its associated modules
        kernel_name = kernel["name"]
        modules = self._get_kernel_modules(kernel_name)

        # All packages to install
        packages = [kernel_name] + modules

        # Start a thread for installation
        threading.Thread(
            target=self._install_kernel_thread,
            args=(packages, progress_callback, output_callback, complete_callback),
            daemon=True,
        ).start()

    def _install_kernel_thread(
        self, packages, progress_callback, output_callback, complete_callback
    ):
        """
        Thread function for kernel installation.

        Args:
            packages: List of packages to install (kernel and modules).
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        if output_callback:
            output_callback(f"Thread started for kernel installation...")

        if progress_callback:
            progress_callback(
                0.1, f"Starting installation of {packages[0]} and modules..."
            )

        # Command for installing the kernel and modules
        cmd = [
            self.package_manager.sudo_command,
            "pacman",
            "-S",
            "--noconfirm",
        ] + packages

        if output_callback:
            output_callback(f"Running command: {' '.join(cmd)}")

        try:
            # Start the process with unbuffered output
            if output_callback:
                output_callback("Creating subprocess...")

            # Create environment with LANG set to ensure consistent output formatting
            my_env = os.environ.copy()
            my_env["LANG"] = "C"  # Use standard C locale for consistent output

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,  # IMPORTANTE: Fornece stdin vazio para evitar bloqueio
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,  # Ensure text mode with universal newlines
                env=my_env,  # Use our custom environment
            )

            if output_callback:
                output_callback("Subprocess created successfully...")

            # Initialize progress tracking variables
            downloading = False
            installing = False
            progress = 0.1
            last_progress_update = time.time()
            last_line_time = time.time()

            # Process output line by line
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                # Send output to callback
                if output_callback and line:
                    output_callback(line)
                    last_line_time = time.time()

                # Parse progress information - be more aggressive in parsing for better feedback
                if (
                    "downloading" in line.lower()
                    or "baixando" in line.lower()
                    or "download" in line.lower()
                ):
                    downloading = True

                    # Try to extract percentage directly
                    percent_match = re.search(r"(\d+)%", line)
                    if percent_match:
                        percent = float(percent_match.group(1))
                        # Scale percentage to our progress range (10%-50%)
                        progress = 0.1 + (percent / 100.0) * 0.4
                        if progress_callback:
                            progress_callback(progress, f"Downloading: {percent:.1f}%")

                    # Alternative approach for download progress
                    match = re.search(r"\((\d+)/(\d+)\)", line)
                    if match:
                        current = int(match.group(1))
                        total = int(match.group(2))
                        progress = (
                            0.1 + (current / total) * 0.4
                        )  # 10%-50% for downloading

                        if progress_callback:
                            progress_callback(
                                progress, f"Downloading packages ({current}/{total})..."
                            )

                    # Provide some feedback even if we can't extract precise progress
                    else:
                        # Only update if we haven't recently
                        current_time = time.time()
                        if current_time - last_progress_update > 1.0:
                            if progress_callback:
                                progress_callback(progress, "Downloading packages...")
                            last_progress_update = current_time

                elif "installing" in line.lower() or "instalando" in line.lower():
                    installing = True
                    if progress_callback:
                        progress_callback(0.5, "Installing kernel...")

                elif installing and (
                    "installed" in line.lower() or "instalado" in line.lower()
                ):
                    # Rough estimation of installation progress
                    progress = min(0.5 + progress * 0.1, 0.9)  # 50%-90% for installing
                    if progress_callback:
                        progress_callback(progress, "Installing...")

                elif (
                    "generating grub configuration file" in line.lower()
                    or "gerando arquivo de configuração do grub" in line.lower()
                ):
                    if progress_callback:
                        progress_callback(0.9, "Updating bootloader...")

                # Additional progress indicators
                elif (
                    "synchronizing package databases" in line.lower()
                    or "sincronizando bases de dados de pacotes" in line.lower()
                ):
                    if progress_callback:
                        progress_callback(0.1, "Synchronizing package databases...")

                elif (
                    "checking dependencies" in line.lower()
                    or "verificando dependências" in line.lower()
                ):
                    if progress_callback:
                        progress_callback(0.2, "Checking dependencies...")

                elif (
                    "checking for file conflicts" in line.lower()
                    or "verificando conflitos de arquivos" in line.lower()
                ):
                    if progress_callback:
                        progress_callback(0.4, "Checking for file conflicts...")

                # Package sizes and totals
                elif (
                    "total download size" in line.lower()
                    or "tamanho total de download" in line.lower()
                ):
                    if output_callback:
                        output_callback("➡️ " + line)

                # Extract package name/version for better progress indication
                pkg_match = re.search(r"(linux\w+)-(\d[\w\.\-]+)", line)
                if pkg_match and installing:
                    pkg_name = pkg_match.group(1)
                    pkg_version = pkg_match.group(2)
                    if progress_callback:
                        progress_callback(
                            progress, f"Installing {pkg_name} {pkg_version}"
                        )

                # Handle common issues
                elif "error:" in line.lower():
                    if output_callback:
                        output_callback(f"❌ ERROR: {line}")

                # Send periodic updates even without new information
                current_time = time.time()
                if current_time - last_progress_update > 0.5:  # Every half second
                    if progress_callback:
                        # Send the same progress to keep UI responsive
                        progress_callback(progress, None)
                    last_progress_update = current_time

                # If no output for more than 5 seconds, send a status message
                if current_time - last_line_time > 5:
                    if output_callback:
                        output_callback(
                            f"Still working... (last action: {progress:.0%} complete)"
                        )
                    last_line_time = current_time

                # Small pause to avoid CPU overload
                time.sleep(0.01)

            if output_callback:
                output_callback("Process completed, checking exit code...")

            # Wait for process to complete
            process.wait()

            # Check if installation was successful
            success = process.returncode == 0

            # Final progress update
            if progress_callback:
                if success:
                    progress_callback(1.0, "Kernel installation complete!")
                else:
                    progress_callback(0.0, "Kernel installation failed.")

            # Final output update
            if output_callback:
                if success:
                    output_callback("✅ Installation completed successfully.")
                else:
                    output_callback(
                        f"❌ Installation failed with return code {process.returncode}."
                    )

            # Notify completion
            if complete_callback:
                complete_callback(success)

        except Exception as e:
            # Handle exceptions
            error_msg = f"Error: {str(e)}"
            print(f"Exception in kernel installation thread: {error_msg}")

            if progress_callback:
                progress_callback(0.0, error_msg)

            if output_callback:
                output_callback(f"❌ {error_msg}")

            if complete_callback:
                complete_callback(False)

    def remove_kernel(
        self,
        kernel,
        progress_callback=None,
        output_callback=None,
        complete_callback=None,
    ):
        """
        Remove a kernel and its modules.

        Args:
            kernel: The kernel to remove (dict with at least "name").
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        # Get the kernel name and its associated modules
        kernel_name = kernel["name"]
        modules = self._get_kernel_modules(kernel_name)

        # All packages to remove
        packages = [kernel_name] + modules

        # Filter for installed packages only
        installed_packages = []
        for pkg in packages:
            if self.package_manager.is_package_installed(pkg):
                installed_packages.append(pkg)

        # Start a thread for removal
        threading.Thread(
            target=self._remove_kernel_thread,
            args=(
                installed_packages,
                progress_callback,
                output_callback,
                complete_callback,
            ),
            daemon=True,
        ).start()

    def _remove_kernel_thread(
        self, packages, progress_callback, output_callback, complete_callback
    ):
        """
        Thread function for kernel removal.

        Args:
            packages: List of packages to remove (kernel and modules).
            progress_callback: Callback function for progress updates.
            output_callback: Callback function for command output.
            complete_callback: Callback function for completion notification.
        """
        if not packages:
            if output_callback:
                output_callback("No packages to remove.")
            if complete_callback:
                complete_callback(True)
            return

        if output_callback:
            output_callback(f"Thread started for kernel removal...")

        if progress_callback:
            progress_callback(0.1, f"Starting removal of {packages[0]} and modules...")

        # Command for removing the kernel and modules
        cmd = [
            self.package_manager.sudo_command,
            "pacman",
            "-R",
            "--noconfirm",
        ] + packages

        if output_callback:
            output_callback(f"Running command: {' '.join(cmd)}")

        try:
            # Start the process with unbuffered output
            if output_callback:
                output_callback("Creating subprocess...")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,  # Ensure text mode with universal newlines
            )

            if output_callback:
                output_callback("Subprocess created successfully...")

            # Initialize tracking variables
            progress = 0.1
            last_progress_update = time.time()
            last_line_time = time.time()
            removal_step = 0
            total_packages = len(packages)
            packages_processed = 0

            # Process output line by line
            for line in iter(process.stdout.readline, ""):
                line = line.strip()
                # Send output to callback
                if output_callback and line:
                    output_callback(line)
                    last_line_time = time.time()

                # Parse progress information based on common messages in pacman output
                if (
                    "checking dependencies" in line.lower()
                    or "verificando dependências" in line.lower()
                ):
                    progress = 0.2
                    removal_step = 1
                    if progress_callback:
                        progress_callback(progress, "Checking dependencies...")

                elif (
                    "looking for conflicting packages" in line.lower()
                    or "procurando por pacotes conflitantes" in line.lower()
                ):
                    progress = 0.3
                    removal_step = 2
                    if progress_callback:
                        progress_callback(
                            progress, "Looking for conflicting packages..."
                        )

                elif "removing" in line.lower() or "removendo" in line.lower():
                    packages_processed += 1
                    # Calculate progress based on packages processed
                    if total_packages > 0:
                        progress = 0.3 + (packages_processed / total_packages) * 0.4
                    else:
                        progress = (
                            0.5  # Default progress if we can't calculate accurately
                        )
                    removal_step = 3
                    if progress_callback:
                        progress_callback(
                            progress,
                            f"Removing packages ({packages_processed}/{total_packages})...",
                        )

                elif (
                    "running post-transaction hooks" in line.lower()
                    or "executando hooks pós-transação" in line.lower()
                ):
                    progress = 0.8
                    removal_step = 4
                    if progress_callback:
                        progress_callback(progress, "Running post-transaction hooks...")

                elif (
                    "generating grub configuration file" in line.lower()
                    or "gerando arquivo de configuração do grub" in line.lower()
                ):
                    progress = 0.9
                    removal_step = 5
                    if progress_callback:
                        progress_callback(0.9, "Updating bootloader...")

                # Handle common issues
                elif "error:" in line.lower():
                    if output_callback:
                        output_callback(f"ERROR: {line}")

                # Calculate progress based on line content if not specifically detected
                elif "image" in line.lower() and "found" in line.lower():
                    # This is during bootloader update process
                    progress = 0.85
                    if progress_callback:
                        progress_callback(
                            progress, "Updating bootloader information..."
                        )

                # Send periodic updates even without new information
                current_time = time.time()
                if current_time - last_progress_update > 0.5:  # Every half second
                    if progress_callback:
                        # Send the same progress to keep UI responsive
                        progress_callback(progress, None)
                    last_progress_update = current_time

                # If no output for more than 5 seconds, send a status message
                if current_time - last_line_time > 5:
                    if output_callback:
                        output_callback(
                            f"Still working... (removal step {removal_step}, {progress:.0%} complete)"
                        )
                    last_line_time = current_time

                # Small pause to avoid CPU overload
                time.sleep(0.01)

            if output_callback:
                output_callback("Process completed, checking exit code...")

            # Wait for process to complete
            process.wait()

            # Check if removal was successful
            success = process.returncode == 0

            # Final progress update
            if progress_callback:
                if success:
                    progress_callback(1.0, "Kernel removal complete!")
                else:
                    progress_callback(0.0, "Kernel removal failed.")

            # Final output update
            if output_callback:
                if success:
                    output_callback("Removal completed successfully.")
                else:
                    output_callback(
                        f"Removal failed with return code {process.returncode}."
                    )

            # Notify completion
            if complete_callback:
                complete_callback(success)

        except Exception as e:
            # Handle exceptions
            error_msg = f"Error: {str(e)}"
            print(f"Exception in kernel removal thread: {error_msg}")

            if progress_callback:
                progress_callback(0.0, error_msg)

            if output_callback:
                output_callback(error_msg)

            if complete_callback:
                complete_callback(False)
