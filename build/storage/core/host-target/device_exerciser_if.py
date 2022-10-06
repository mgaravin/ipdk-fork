# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

from fio_args import FioArgs
from volume import VolumeId


class DeviceExerciserError(RuntimeError):
    pass


class DeviceExerciserIf:
    def run_fio(
        self, device_handle: str, volume_ids: set[VolumeId], fio_args: FioArgs
    ) -> str:
        raise NotImplementedError()
