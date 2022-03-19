#!/usr/bin/env python

from ctypes import *

class Ch341Par:

    def __init__(self, device_id):
        self.device_id = device_id
        self.ch341dll = windll.CH341DLL

    def __enter__(self):
        self.handle = self.open_device()
        if self.handle == -1:
            raise Exception("Cannot open device id {0}".format(self.device_id))
        return self

    def __exit__(self, exc_type, exc_value, trace):
        if self.handle != -1:
            self.close_device()

    def open_device(self):
        open_device = self.ch341dll.CH341OpenDevice
        open_device.argtypes = [c_ulong]
        open_device.restype = c_int
        return open_device(self.device_id)

    def close_device(self):
        close_device = self.ch341dll.CH341CloseDevice
        close_device.argtypes = [c_ulong]
        close_device(self.device_id)

    def get_device_name(self):
        get_device_name = self.ch341dll.CH341GetDeviceName
        get_device_name.argtypes = [c_ulong]
        get_device_name.restype = c_char_p
        return get_device_name(self.device_id)

    def set_stream(self, i_mode):
        set_stream = self.ch341dll.CH341SetStream
        # iMode
        # Bit 1 bit 0: I2C interface speed / SCL frequency, 00 = low speed / 20KHz, 01 = standard / 100KHz (default), 10 = fast / 400KHz, 11 = high speed / 750KHz
        # Bit 2: SPI I / O count / IO pin, 0 = single entry (D3 clock / D5 out / D7 in) (default), 1 = double entry double (D3 clock / D5 out D4 out / D7 into D6 into)
        # Bit 7: bit order in SPI byte, 0 = low first, 1 = high first
        # Other bits must be 0
        set_stream.argtypes = [c_ulong, c_ulong]    # iIndex, iMode
        set_stream.restype = c_bool
        if not set_stream(self.device_id, i_mode):
            raise Exception("Failed to set stream")

    def stream_spi_4(self, i_chip_select, i_length, io_buffer):
        # BOOL	WINAPI	CH341StreamSPI4(  // Processing the SPI data stream, 4-wire interface, the clock line for the DCK / D3 pin, 
        #                                    the output data line DOUT / D5 pin, the input data line for the DIN / D7 pin, 
        #                                    chip line for the D0 / D1 / D2, the speed of about 68K bytes
        #                                 /* SPI Timing: The DCK / D3 pin is clocked and defaults to the low level. 
        #                                    The DOUT / D5 pin is output during the low period before the rising edge of the clock. 
        #                                    The DIN / D7 pin is at a high level before the falling edge of the clock enter */
        # 	ULONG			iIndex,       // Specify the CH341 device serial number
        # 	ULONG			iChipSelect,  // Chip select control, bit 7 is 0 is ignored chip select control, 
        #                                    bit 7 is 1 parameter is valid: bit 1 bit 0 is 00/01/10 select D0 / D1 / D2 pin as low active chip select
        # 	ULONG			iLength,      // The number of bytes of data to be transferred
        # 	PVOID			ioBuffer );   // Point to a buffer, place the data to be written from DOUT, and return the data read from DIN
        stream_spi_4 = self.ch341dll.CH341StreamSPI4
        stream_spi_4.argtypes = [c_ulong, c_ulong, c_ulong, POINTER(c_char)]
        stream_spi_4.restype = c_bool
        if not stream_spi_4(self.device_id, i_chip_select, i_length, io_buffer):
            raise Exception("SPI transfer failed")
