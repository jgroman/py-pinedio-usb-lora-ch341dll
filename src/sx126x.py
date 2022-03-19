#!/usr/bin/env python

from ctypes import *
from typing import Tuple

from ch341par import Ch341Par


def trace(func):
    def wrapper(*args, **kwargs):
        print(f'? {func.__name__}')

        original_result = func(*args, **kwargs)

        print(f'! {func.__name__}: {original_result}')

        return original_result
    return wrapper


class Sx126x:

    def __init__(self, ch341_device_id: int, ch341_stream_mode: int, ch341_chip_select: int):
        self.buffer = create_string_buffer(100)

        self.ch341_device_id = ch341_device_id
        self.ch341_stream_mode = ch341_stream_mode
        self.ch341_chip_select = ch341_chip_select

        # Set device stream mode
        with Ch341Par(self.ch341_device_id) as device:
            print(device.get_device_name())
            device.set_stream(self.ch341_stream_mode)

    def _send_command(self, cmd_bytes: bytes, read_byte_count: int) -> bytes:
        self.buffer.value = cmd_bytes
        write_byte_count = len(cmd_bytes)

        print("> [{}] {}".format(write_byte_count, cmd_bytes.hex()))

        with Ch341Par(self.ch341_device_id) as device:
            device.stream_spi_4(self.ch341_chip_select, write_byte_count, self.buffer)
        print("< [{}] {}".format(read_byte_count, bytes(self.buffer[:read_byte_count]).hex()))

        return bytes(self.buffer[:read_byte_count])

    # ==== 13.1 Operational Modes Functions

    def SetSleep(self):
        pass

    @trace
    def SetStandby(self, stdby_config) -> None:
        """
        13.1.2 SetStandby
        The command SetStandby(...) is used to set the device in a configuration 
        mode which is at an intermediate level of consumption. In this mode, 
        the chip is placed in halt mode waiting for instructions via SPI. 
        This mode is dedicated to chip configuration using high level commands 
        such as SetPacketType(...).
        By default, after battery insertion or reset operation (pin NRESET goes 
        low), the chip will enter in STDBY_RC mode running with a 13 MHz RC clock.
        StdbyConfig:
         0 STDBY_RC    Device running on RC13M, set STDBY_RC mode
         1 STDBY_XOSC  Device running on XTAL 32MHz, set STDBY_XOSC mode        
        """
        self._send_command(bytes([0x80, stdby_config & 0x01]), 2)

    # ==== 13.2 Registers and Buffer Access

    def ReadRegister(self, reg_address, length):
        self.buffer[0] = 0x1D
        self.buffer[1] = reg_address & 0xFF00
        self.buffer[2] = reg_address & 0x00FF
        for i in range(length+1):
            self.buffer[3 + i] = 0
        with Ch341Par(self.ch341_device_id) as device:
            device.stream_spi_4(self.ch341_chip_select, 3 + length, self.buffer)

    # ==== 13.3 DIO and IRQ Control Functions

    # ==== 13.4 RF Modulation and Packet-Related Functions

    @trace
    def SetPacketType(self, packet_type) -> None:
        """
        13.4.2 SetPacketType
        The command SetPacketType(...) sets the SX1261 radio in LoRa® or in FSK 
        mode. The command SetPacketType(...) must be the first of the radio 
        configuration sequence. The parameter for this command is PacketType.
        The switch from one frame to another must be done in STDBY_RC mode.
        PacketType: 0 - GFSK, 1 - LoRa
        """
        self._send_command(bytes([0x8A, packet_type & 0x01]), 2)

    @trace
    def GetPacketType(self):
        """
        13.4.3 GetPacketType
        The command GetPacketType() returns the current operating packet type 
        of the radio.
        PacketType: 0 - GFSK, 1 - LoRa
        """
        res_bytes = self._send_command(bytes.fromhex('11 00 00'), 3)
        return {
            'Status': res_bytes[1],
            'packetType': res_bytes[2],
        }

    # ==== 13.5 Communication Status Information

    @trace
    def GetStatus(self) -> int:
        """
        13.5.1 GetStatus
        The host can retrieve chip status directly through the command GetStatus(): 
        this command can be issued at any time and the device returns the status 
        of the device. The command GetStatus() is not strictly necessary since 
        device returns status information also on command bytes.
        Bit definition:
        7    Reserved
        6:4  Chip Mode
             0  Unused
             2  STBY_RC
             3  STBY_XOSC
             4  FS
             5  RX
             6  TX
        3:1  Command status
             0  Reserved
             2  Data is available to host
             3  Command timeout
             4  Command processing error
             5  Failure to execute command
             6  Command TX done
        0    Reserved
        """
        res_bytes = self._send_command(bytes.fromhex('C0 00'), 2)
        return res_bytes[1]

    @trace
    def GetRxBufferStatus(self):
        """
        13.5.2 GetRxBufferStatus
        This command returns the length of the last received packet (PayloadLengthRx) 
        and the address of the first byte received (RxStartBufferPointer). It is 
        applicable to all modems. The address is an offset relative to the first 
        byte of the data buffer.
        """
        res_bytes = self._send_command(bytes.fromhex('13 00 00 00'), 4)
        return {
            'Status': res_bytes[1],
            'PayloadLengthRx': res_bytes[2],
            'RxStartBufferPointer': res_bytes[3],
        }
