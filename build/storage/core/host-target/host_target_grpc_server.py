#!/usr/bin/env python
#
# Copyright (C) 2022 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#

import grpc
import logging
import host_target_pb2
import host_target_pb2_grpc
from concurrent import futures
from grpc_reflection.v1alpha import reflection
from device_exerciser_kvm import DeviceExerciserKvm
from device_exerciser_if import *
from device_exerciser_customization import find_make_custom_device_exerciser
from helpers.fio_args import FioArgs, FioArgsError
from volumes import VolumeId


class HostTargetService(host_target_pb2_grpc.HostTargetServicer):
    def __init__(
        self,
        device_exerciser,
    ):
        super().__init__()
        self._device_exerciser = device_exerciser

    def RunFio(self, request, context):
        logging.info(f"RunFio: request:'{request}'")
        output = None
        try:
            volume_ids = set()
            for volume_id in request.diskToExercise.volumeId:
                logging.info(f"volume id to exercise is `{volume_id}`")
                volume_ids.add(VolumeId(volume_id))

            output = self._device_exerciser.run_fio(
                request.diskToExercise.deviceHandle,
                volume_ids,
                FioArgs(request.fioArgs),
            )
        except BaseException as ex:
            logging.error("Service exception: '" + str(ex) + "'")
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(ex))
        return host_target_pb2.RunFioReply(fioOutput=output)

    def PlugDevice(self, request, context):
        logging.info(f"PlugDevice: request:'{request}'")
        try:
            device_handle = request.deviceHandle
            self._device_exerciser.plug_device(device_handle)
        except BaseException as ex:
            logging.error("Service exception: '" + str(ex) + "'")
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(ex))
        return host_target_pb2.RunFioReply()

    def UnplugDevice(self, request, context):
        logging.info(f"UnplugDevice: request:'{request}'")
        try:
            device_handle = request.deviceHandle
            self._device_exerciser.unplug_device(device_handle)
        except BaseException as ex:
            logging.error("Service exception: '" + str(ex) + "'")
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(ex))
        return host_target_pb2.RunFioReply()


def make_default_device_exerciser() -> DeviceExerciserIf:
    return DeviceExerciserKvm()


def get_device_exerciser(
    customization_path,
    find_make_custom_device_exerciser=find_make_custom_device_exerciser,
) -> DeviceExerciserIf:
    make_custom_device_exerciser = find_make_custom_device_exerciser(customization_path)
    device_exerciser = None
    if make_custom_device_exerciser:
        logging.info(
            "Function to create customized exerciser is provided. Creating one."
        )
        device_exerciser = make_custom_device_exerciser()
    else:
        logging.info("Use default device exerciser.")
        device_exerciser = make_default_device_exerciser()
    if not device_exerciser or not issubclass(
        type(device_exerciser), DeviceExerciserIf
    ):
        raise RuntimeError("No device exerciser created.")

    return device_exerciser


def run_grpc_server(
    ip_address,
    port,
    customization_dir,
    server_creator=grpc.server,
):
    try:
        server = server_creator(futures.ThreadPoolExecutor(max_workers=10))
        host_target_pb2_grpc.add_HostTargetServicer_to_server(
            HostTargetService(get_device_exerciser(customization_dir)), server
        )
        service_names = (
            host_target_pb2.DESCRIPTOR.services_by_name["HostTarget"].full_name,
            reflection.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, server)
        server.add_insecure_port(ip_address + ":" + str(port))
        server.start()
        server.wait_for_termination()
        return 0
    except KeyboardInterrupt as ex:
        return 0
    except BaseException as ex:
        logging.error("Couldn't run gRPC server. Error: " + str(ex))
        return 1
