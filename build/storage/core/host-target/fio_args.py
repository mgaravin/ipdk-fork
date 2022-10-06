# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

import json
import tempfile
import typing
from volume import Volume


class FioArgsError(ValueError):
    pass


class FioArgs:
    class Config:
        def __init__(self, owner: "FioArgs") -> None:
            self._owner = owner
            self._file = None
            self.file_name = ""

        def __enter__(self):
            self._file = tempfile.NamedTemporaryFile()
            self.file_name = self._file.name

            with open(self.file_name, "w") as config:
                self._dump_owner_to_file(config)

            self._file.__enter__()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb) -> None:
            self._file.__exit__(exc_type, exc_val, exc_tb)

        def _dump_owner_to_file(self, file: typing.TextIO) -> None:
            file.write("[job0]\n")
            for arg_key in self._owner._fio_args:
                if arg_key == self._owner._volume_to_exercise_option:
                    file.write(
                        arg_key
                        + "="
                        + ":".join(map(str, self._owner._fio_args[arg_key]))
                        + "\n"
                    )
                else:
                    file.write(
                        arg_key + "=" + str(self._owner._fio_args[arg_key]) + "\n"
                    )
            file.flush()

    def __init__(self, fio_args_str: str) -> None:
        self._volume_to_exercise_option = "filename"
        try:
            self._fio_args = json.loads(fio_args_str)
            if self._volume_to_exercise_option in self._fio_args:
                raise FioArgsError(
                    "Explicitly specify filename as argument is not allowed."
                )
        except (json.JSONDecodeError, TypeError) as err:
            raise FioArgsError(str(err))

    def add_volumes_to_exercise(self, volumes_to_exercise: set[Volume]):
        if self._volume_to_exercise_option not in self._fio_args:
            self._fio_args[self._volume_to_exercise_option] = []
        self._fio_args[self._volume_to_exercise_option] = list(
            volumes_to_exercise.union(self._fio_args[self._volume_to_exercise_option])
        )

    def add_argument(self, key: str, value: str) -> None:
        self._fio_args[key] = value

    def create_config_file(self) -> Config:
        return FioArgs.Config(self)

    def __str__(self) -> str:
        return json.dumps(self._fio_args)
