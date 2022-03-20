#!/usr/bin/env python
"""

Note: public variable and function names are quoted verbatim from Sx126x datasheet.
"""

from ctypes import *
from typing import Dict

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

    def _send_command(self, cmd_bytes: bytes) -> bytes:
        self.buffer.value = cmd_bytes
        byte_count = len(cmd_bytes)

        with Ch341Par(self.ch341_device_id) as device:
            device.stream_spi_4(self.ch341_chip_select, byte_count, self.buffer)
        print("[{}] {} > {}".format(byte_count, cmd_bytes.hex(), bytes(self.buffer[:byte_count]).hex()))

        return bytes(self.buffer[:byte_count])

    # ==== 13.1 Operational Modes Functions

    @trace
    def SetSleep(self, sleepConfig: int) -> None:
        """
        Set the device in SLEEP mode with the lowest current consumption possible.
        This command can be sent only while in STDBY mode (STDBY_RC or STDBY_XOSC). 
        After the rising edge of NSS, all blocks are switched OFF except the backup
        regulator if needed and the blocks specified in the parameter sleepConfig.
        sleepConfig bits
        [7:3]  RESERVED
        [2]    0 - cold start, 1 - warm start
        [1]    RFU
        [0]    0 - RTC timeout disable, 1 - wake-up on RTC timeout (RC64k)
        """
        self._send_command(bytes([0x84, sleepConfig & 0xFF]))

    @trace
    def SetStandby(self, StdbyConfig: int) -> None:
        """
        Set the device in a configuration mode which is at an intermediate level 
        of consumption. In this mode, the chip is placed in halt mode waiting 
        for instructions via SPI.
        This mode is dedicated to chip configuration using high level commands 
        such as SetPacketType().
        By default, after battery insertion or reset operation (pin NRESET goes 
        low), the chip will enter in STDBY_RC mode running with a 13 MHz RC clock.
        StdbyConfig:
         0 STDBY_RC    Device running on RC13M, set STDBY_RC mode
         1 STDBY_XOSC  Device running on XTAL 32MHz, set STDBY_XOSC mode        
        """
        self._send_command(bytes([0x80, StdbyConfig & 0x01]))

    @trace
    def SetFs(self) -> None:
        """
        Set the device in the frequency synthesis mode where the PLL is locked 
        to the carrier frequency. This mode is used for test purposes of the PLL
        and can be considered as an intermediate mode. It is automatically 
        reached when going from STDBY_RC mode to TX mode or RX mode.
        In FS mode, the PLL will be set to the frequency programmed by 
        the function SetRfFrequency() which is the same used for TX or RX 
        operations.
        """
        self._send_command(b'\xC1')

    @trace
    def SetTx(self, timeout: int) -> None:
        """
        Set the device in transmit mode.
        - Starting from STDBY_RC mode, the oscillator is switched ON followed by 
          the PLL, then the PA is switched ON and the PA regulator starts ramping 
          according to the ramping time defined by the command SetTxParams()
        - When the ramping is completed the packet handler starts the packet transmission
        - When the last bit of the packet has been sent, an IRQ TX_DONE is generated, 
          the PA regulator is ramped down, the PA is switched OFF and the chip goes 
          back to STDBY_RC mode
        - A TIMEOUT IRQ is triggered if the TX_DONE IRQ is not generated within 
          the given timeout period
        - The chip goes back to STBY_RC mode after a TIMEOUT IRQ or a TX_DONE IRQ.
        Timeout duration = Timeout * 15.625 µs
        Timeout[23:0]
        0x000000 Timeout disable, Tx Single mode, the device will stay in TX Mode until 
                 the packet is transmitted and returns in STBY_RC mode upon completion.
        others   Timeout active, the device remains in TX mode, it returns automatically 
                 to STBY_RC mode on timer end-of-count or when a packet has been transmitted. 
                 The maximum timeout is then 262 s.
        """
        self._send_command(b'\x83' + timeout.to_bytes(3, 'big'))

    @trace
    def SetRx(self, timeout: int) -> None:
        """
        Sets the chip in RX mode, waiting for the reception of one or several packets. 
        The receiver mode operates with a timeout to provide maximum flexibility 
        to end users.
        When the timeout is active (0x000000 < timeout < 0xFFFFFF), the radio will 
        stop the reception at the end of the timeout period unless a preamble and 
        Sync Word (in GFSK) or Header (in LoRa®) has been detected. This is 
        to ensure that a valid packet will not be dropped in the middle of 
        the reception due to the pre-defined timeout. By default, the timer will be
        stopped only if the Sync Word or header has been detected. However, it is 
        also possible to stop the timer upon preamble detection by using 
        the command StopTimerOnPreamble().
        Timeout[23:0]
        0x000000 No timeout. Rx Single mode. The device will stay in RX Mode until 
                 a reception occurs and the devices return in STBY_RC mode upon 
                 completion
        0xFFFFFF Rx Continuous mode. The device remains in RX mode until the host 
                 sends a command to change the operation mode. The device can receive 
                 several packets. Each time a packet is received, a packet done
                 indication is given to the host and the device will automatically 
                 search for a new packet.
        others   Timeout active. The device remains in RX mode, it returns automatically 
                 to STBY_RC mode on timer end-of-count or when a packet has been received. 
                 As soon as a packet is detected, the timer is automatically disabled 
                 to allow complete reception of the packet. 
                 The maximum timeout is then 262 s.
        """
        self._send_command(b'\x82' + timeout.to_bytes(3, 'big'))

    @trace
    def StopTimerOnPreamble(self, StopOnPreambleParam: int) -> None:
        """
        Allows the user to select if the timer is stopped upon preamble detection of Sync
        Word / header detection.
        By default, the timer is stopped only when the Sync Word (in GFSK) or 
        Header (in LoRa®) has been detected. When the function StopTimerOnPreamble() 
        is used with the value enable at 0x01, then the timer will be stopped upon preamble
        detection and the device will stay in RX mode until a packet is received. 
        It is important to notice that stopping the timer upon preamble may cause 
        the device to stay in Rx for an unexpected long period of time 
        in case of false detection.
        StopOnPreambleParam:
        0 - disable, Timer is stopped upon Sync Word or Header detection
        1 - enable, Timer is stopped upon preamble detection
        """
        self._send_command(bytes([0x9F, StopOnPreambleParam & 0x01]))

    @trace
    def SetRxDutyCycle(self, rxPeriod: int, sleepPeriod: int) -> None:
        """
        Sets the chip in sniff mode so that it regularly looks for new packets. 
        This is the listen mode.
        When this command is sent in STDBY_RC mode, the context (device configuration) 
        is saved and the chip enters in a loop defined by the following steps:
        - The chip enters RX and listens for a packet for a period of time defined by rxPeriod
        - The chip is looking for a preamble in either LoRa® or FSK
        - Upon preamble detection, the timeout is stopped and restarted with 
          the value 2 * rxPeriod + sleepPeriod
        - If no packet is received during the RX window (defined by rxPeriod), 
          the chip goes into SLEEP mode with context saved for a period of time 
          defined by sleepPeriod
        - At the end of the SLEEP window, the chip automatically restarts the process 
          of restoring context and enters the RX mode, and so on. 
        At any time, the host can stop the procedure. The loop is terminated if either:
        - A packet is detected during the RX window, at which moment the chip 
          interrupts the host via the RX_DONE flag and returns to STBY_RC mode
        - The host issues a SetStandby() command during the RX window (during 
          SLEEP mode, the device is unable to receive commands straight away and 
          must first be waken up by a falling edge of NSS).
        Rx Duration    = rxPeriod    * 15.625 µs
        Sleep Duration = sleepPeriod * 15.625 µs
        """
        cmd_bytes = b'\x94' + rxPeriod.to_bytes(3, 'big')
        cmd_bytes += sleepPeriod.to_bytes(3, 'big')
        self._send_command(cmd_bytes)

    @trace
    def SetCAD(self) -> None:
        """
        This command can be used only in LoRa® packet type. The Channel Activity 
        Detection is a LoRa® specific mode of operation where the device searches
        for the presence of a LoRa® preamble signal. After the search has completed, 
        the device returns in STDBY_RC mode. The length of the search is configured 
        via the command SetCadParams(). At the end of the search period, the device 
        triggers the IRQ CADdone if it has been enabled. If a valid signal has been 
        detected it also generates the IRQ CadDetected.
        """
        self._send_command(b'\xC5')

    @trace
    def SetTxContinuousWave(self) -> None:
        """
        Test command available for all packet types to generate a continuous wave 
        (RF tone) at selected frequency and output power. The device stays in TX 
        continuous wave until the host sends a mode configuration command.
        """
        self._send_command(b'\xD1')

    @trace
    def SetTxInfinitePreamble(self) -> None:
        """
        Test command to generate an infinite sequence of alternating zeros and ones 
        in FSK modulation. In LoRa®, the radio is only able to constantly modulate 
        LoRa® preamble symbols. The device will remain in TX infinite preamble until 
        the host sends a mode configuration command.
        However, when using this function, it is impossible to define any data sent
        by the device. In LoRa® mode, the radio is only able to constantly modulate 
        LoRa preamble symbols and, in FSK mode, the radio is only able to generate 
        FSK preamble (0x55). 
        """
        self._send_command(b'\xD2')

    @trace
    def SetRegulatorMode(self, regModeParam: int) -> None:
        """
        By default only the LDO is used. This is useful in low cost applications 
        where the cost of the extra self needed for a DC-DC converter is prohibitive. 
        Using only a linear regulator implies that the RX or TX current is almost 
        doubled. This function allows to specify if DC-DC or LDO is used for power 
        regulation. The regulation mode is defined by parameter regModeParam.
        Note: This function is clearly related to the hardware implementation of 
        the device. The user should always use this command while knowing what 
        has been implemented at the hardware level.
        regModeParam:
        0 Only LDO used for all modes
        1 DC_DC+LDO used for STBY_XOSC,FS, RX and TX modes
        """
        self._send_command(bytes([0x96, regModeParam & 0x01]))

    @trace
    def Calibrate(self, calibParam: int) -> None:
        """
        At power up the radio performs calibration of RC64k, RC13M, PLL and ADC. 
        It is however possible to launch a calibration of one or several blocks 
        at any time starting in STDBY_RC mode. The calibrate function starts 
        the calibration of a block defined by calibParam.
        The total calibration time if all blocks are calibrated is 3.5 ms. 
        The calibration must be launched in STDBY_RC mode and the BUSY pins will 
        be high during the calibration process. A falling edge of BUSY indicates 
        the end of the procedure.
        calibParam  bit value 0 - block calibration disabled, 1 - enabled
        [0] RC64k
        [1] RC13M
        [2] PLL
        [3] ADC pulse
        [4] ADC bulk N
        [5] ADC bulk P
        [6] Image
        [7] RFU, 0 only
        """
        self._send_command(bytes([0x89, calibParam & 0xFF]))

    @trace
    def CalibrateImage(self, freq1: int, freq2: int) -> None:
        """
        Allows the user to calibrate the image rejection of the device for 
        the device operating frequency band.
        Band [MHz] / freq1 / freq2
        430 - 440    0x6B    0x6F
        470 - 510    0x75    0x81
        779 - 787    0xC1    0xC5
        863 - 870    0xD7    0xDB
        902 - 928    0xE1    0xE9    (default)
        """
        self._send_command(bytes([0x98, freq1 & 0xFF, freq2 & 0xFF]))

    @trace
    def SetPaConfig(self, paDutyCycle: int, hpMax: int, deviceSel: int) -> None:
        """
        The command which is used to differentiate the SX1261 from the SX1262. 
        When using this command, the user selects the PA to be used by the device 
        as well as its configuration.
        - paDutyCycle controls the duty cycle (conduction angle) of both PAs 
          (SX1261 and SX1262). The maximum output power, the power consumption, 
          and the harmonics will drastically change with paDutyCycle
        - hpMax selects the size of the PA in the SX1262, this value has no influence 
          on the SX1261. The maximum output power can be reduced by reducing 
          the value of hpMax. The valid range is between 0x00 and 0x07 and 0x07 is 
          the maximum supported value for the SX1262 to achieve +22 dBm output power.
        - deviceSel is used to select either the SX1261 or the SX1262.
        """
        cmd_bytes = b'\x95' 
        cmd_bytes += paDutyCycle & 0x07
        cmd_bytes += hpMax & 0x07
        cmd_bytes += deviceSel & 0x01
        cmd_bytes += b'\x01'  # paLut is always 0x01
        self._send_command(cmd_bytes)

    @trace
    def SetRxTxFallbackMode(self, fallbackMode: int) -> None:
        """
        This command defines into which mode the chip goes after a successful 
        transmission or after a packet reception.
        By default, the radio will always return in STDBY_RC unless 
        the configuration is changed by using this command. Changing the default
        mode from STDBY_RC to STDBY_XOSC or FS will only have an impact on 
        the switching time of the radio.
        Fallback mode:
        0x40  FS        The radio goes into FS mode 
        0x30  STBY_XOSC The radio goes into STDBY_XOSC mode
        0x20  STDBY+RC  The radio goes into STDBY_RC mode
        """
        self._send_command(bytes([0x93, fallbackMode & 0xFF]))

    # ==== 13.2 Registers and Buffer Access

    @trace
    def WriteRegister(self, write_address: int, write_bytes: bytes) -> Dict[str, bytes]:
        """
        Allows writing a block of bytes in a data memory space starting at a specific 
        address. The address is auto incremented after each data byte so that 
        data is stored in contiguous memory locations.
        """
        cmd_bytes = b'\x0D'
        cmd_bytes += write_address.to_bytes(2, 'big')
        cmd_bytes += write_bytes
        cmd_result = self._send_command(cmd_bytes)
        print("WriteRegister (0x{:04X}): {}".format(write_address, bytes(cmd_result[4:])))
        return {
            'status': cmd_result[1],
        }

    @trace
    def ReadRegister(self, read_address: int, read_length: int) -> Dict[str, bytes]:
        """
        Allows reading a block of data starting at a given address. The address 
        is auto-incremented after each byte. Note that the host has to send 
        an NOP after sending the 2 bytes of address to start receiving data 
        bytes on the next NOP sent.
        """
        cmd_bytes = b'\x1D'
        cmd_bytes += read_address.to_bytes(2, 'big')
        cmd_bytes += bytes(read_length + 1)
        cmd_result = self._send_command(cmd_bytes)
        print("ReadRegister (0x{:04X}): {}".format(read_address, bytes(cmd_result[4:])))
        return {
            'status': cmd_result[3],
            'data': cmd_result[4:],
        }

    @trace
    def WriteBuffer(self, offset: int, write_bytes: bytes) -> Dict[str, bytes]:
        """
        This function is used to store data payload to be transmitted. The address 
        is auto-incremented; when it exceeds the value of 255 it is wrapped back 
        to 0 due to the circular nature of the data buffer. The address starts 
        with an offset set as a parameter of the function. 
        """
        cmd_bytes = b'\x0E'
        cmd_bytes += bytes([offset & 0xFF])
        cmd_bytes += write_bytes
        cmd_result = self._send_command(cmd_bytes)
        print("WriteBuffer (0x{:02X}): {}".format(offset, bytes(cmd_result[2:])))
        return {
            'status': cmd_result[1],
        }

    @trace
    def ReadBuffer(self, offset: int, read_length: int) -> Dict[str, bytes]:
        """
        Allows reading bytes of payload received starting at offset. Note that 
        the NOP must be sent after sending the offset.
        """
        cmd_bytes = b'\x1E'
        cmd_bytes += bytes([offset & 0xFF])
        cmd_bytes += bytes(read_length + 1)
        cmd_result = self._send_command(cmd_bytes)
        print("ReadBuffer (0x{:02X}): {}".format(offset, bytes(cmd_result[3:])))
        return {
            'status': cmd_result[2],
            'data': cmd_result[3:],
        }

    # ==== 13.3 DIO and IRQ Control Functions

    @trace
    def SetDioIrqParams(self, IrqMask: int, DIO1Mask: int, DIO2Mask: int, DIO3Mask: int) -> None:
        """
        This command is used to set the IRQ flag.
        - IrqMask: masks or unmasks the IRQ which can be triggered by the device. 
          By default, all IRQ are masked (all 0) and the user can enable them one 
          by one (or several at a time) by setting the corresponding mask to 1.
        - DIOxMask: The interrupt causes a DIO to be set if the corresponding bit 
          in DioxMask and the IrqMask are set. As an example, if bit 0 of IrqMask 
          is set to 1 and bit 0 of DIO1Mask is set to 1 then, a rising edge of IRQ 
          source TxDone will be logged in the IRQ register and will appear at 
          the same time on DIO1.
          One IRQ can be mapped to all DIOs, one DIO can be mapped to all IRQs 
          (an OR operation is done) but some IRQ sources will be available only 
          on certain modes of operation and frames.
        In total there are 10 possible interrupt sources depending on the chosen 
        frame and chip mode. Each one of them can be enabled or masked. In addition,
        every one of them can be mapped to DIO1, DIO2 or DIO3. Note that if DIO2 
        or DIO3 are used to control the RF Switch or the TCXO, the IRQ will not 
        be generated even if it is mapped to the pins.
        IRQ Register Bits:
        [0] TxDone             Packet transmission completed
        [1] RxDone             Packet received
        [2] PreambleDetected   Preamble detected
        [3] SyncWordValid      Valid sync word detected  (FSK only)
        [4] HeaderValid        Valid LoRa header received  (LoRa only)
        [5] HeaderErr          LoRa header CRC error  (LoRa only)
        [6] CrcErr             Wrong CRC received
        [7] CadDone            Channel activity detection finished  (LoRa only)
        [8] CadDetected        Channel activity detected  (LoRa only)
        [9] Timeout            Rx or Tx timeout
        """
        cmd_bytes = b'\x08'
        cmd_bytes += IrqMask.to_bytes(2, 'big')
        cmd_bytes += DIO1Mask.to_bytes(2, 'big')
        cmd_bytes += DIO2Mask.to_bytes(2, 'big')
        cmd_bytes += DIO3Mask.to_bytes(2, 'big')
        self._send_command(cmd_bytes)

    @trace
    def GetIrqStatus(self) -> Dict[str, bytes]:
        """
        This command returns the value of the IRQ register. A dedicated 10-bit 
        register called IRQ_reg is used to log IRQ sources. Each position 
        corresponds to one IRQ source.
        """
        cmd_result = self._send_command(b'\x12\x00\x00\x00')
        return {
            'status': cmd_result[1],
            'IrqStatus': cmd_result[2:],
        }


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
        res_bytes = self._send_command(b'\xC0\x00')
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
        res_bytes = self._send_command(b'\x13\x00\x00\x00', 4)
        return {
            'Status': res_bytes[1],
            'PayloadLengthRx': res_bytes[2],
            'RxStartBufferPointer': res_bytes[3],
        }
