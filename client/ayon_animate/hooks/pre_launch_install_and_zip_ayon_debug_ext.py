"""Debug-only hook to rebuild and install the Animate extension.

Equivalent command used for signing:
C:\scripts\ZXPSignCmd.exe -sign
"<addon_root>\\api\\extension"
"<addon_root>\\api\\extension.zxp"
"C:\scripts\cert.p12"
"<cert_password>"
"""

import os
import subprocess
from pathlib import Path
from shutil import rmtree
from zipfile import ZipFile

import platformdirs

from ayon_animate import ANIMATE_ADDON_ROOT
from ayon_applications import LaunchTypes, PreLaunchHook


class DEBUGInstallAyonExtensionToAnimate(PreLaunchHook):
    """Build and reinstall Animate CEP extension on every local launch."""

    app_groups = {"animate"}
    order = 1
    launch_types = {LaunchTypes.local}

    signer_executable = Path("C:/scripts/ZXPSignCmd.exe")
    certificate_path = Path("C:/scripts/cert.p12")
    certificate_password_env = "AYON_ANIMATE_ZXP_CERT_PASSWORD"

    def execute(self):
        try:
            self.inner_execute()

        except Exception:
            self.log.warning(
                "Processing of {} crashed.".format(self.__class__.__name__),
                exc_info=True,
            )

    def inner_execute(self):
        self.log.info("Rebuilding and reinstalling AYON Animate extension.")

        extension_source_path = Path(ANIMATE_ADDON_ROOT, "api", "extension")
        extension_zxp_path = Path(ANIMATE_ADDON_ROOT, "api", "extension.zxp")
        target_path = Path(
            platformdirs.user_data_dir(roaming=True),
            "Adobe/CEP/extensions/io.ynput.FLA.panel",
        )

        self._create_zxp(extension_source_path, extension_zxp_path)
        self._reinstall_extension(target_path, extension_zxp_path)

    def _create_zxp(self, extension_source_path: Path, extension_zxp_path: Path):
        if not self.signer_executable.exists():
            raise RuntimeError(
                "ZXP signer executable not found: {}".format(self.signer_executable)
            )

        if not self.certificate_path.exists():
            raise RuntimeError(
                "ZXP certificate not found: {}".format(self.certificate_path)
            )

        if not extension_source_path.is_dir():
            raise RuntimeError(
                "Extension source folder not found: {}".format(extension_source_path)
            )

        cert_password = os.getenv(self.certificate_password_env)

        if extension_zxp_path.exists():
            extension_zxp_path.unlink()

        command = [
            str(self.signer_executable),
            "-sign",
            str(extension_source_path),
            str(extension_zxp_path),
            str(self.certificate_path),
            cert_password,
        ]
        self.log.debug("Creating zxp from extension source directory.")
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                "Failed to create extension zxp. stdout: {} stderr: {}".format(
                    result.stdout,
                    result.stderr,
                )
            )

        self.log.info("Successfully created extension zxp: {}".format(extension_zxp_path))

    def _reinstall_extension(self, target_path: Path, extension_zxp_path: Path):
        if target_path.exists():
            self.log.info("Removing existing extension at {}".format(target_path))
            rmtree(target_path)

        self.log.debug("Creating extension directory: {}".format(target_path))
        target_path.mkdir(parents=True, exist_ok=True)

        with ZipFile(extension_zxp_path, "r") as archive:
            archive.extractall(path=target_path)

        self.log.info("Successfully installed AYON extension")
