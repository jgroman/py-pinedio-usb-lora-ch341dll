#!/usr/bin/env python

from ch341par import *
from sx126x import Sx126x

ch341_device_id = 0
ch341_stream_mode = 0x80   # SPI: MSB first, single line
ch341_chip_select = 0x80   # SPI: Chip select is on CH341/D0 pin

sx = Sx126x(ch341_device_id, ch341_stream_mode, ch341_chip_select)

status = sx.GetStatus()
print("GetStatus: 0x{:02X}".format(status))

packet_type = sx.GetPacketType()
print("GetPacketType: {}".format(packet_type))

sx.SetPacketType(1)

packet_type = sx.GetPacketType()
print("GetPacketType: {}".format(packet_type))

sx.SetPacketType(0)

packet_type = sx.GetPacketType()
print("GetPacketType: {}".format(packet_type))
