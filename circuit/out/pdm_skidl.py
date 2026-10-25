"""SKiDL source, regenerated from design.py.

Run where KiCad symbol libraries exist:
    python3 pdm_skidl.py      # writes pdm_rig.net
"""
import os
os.environ.setdefault("KICAD_SYMBOL_DIR", "/usr/share/kicad/symbols")
from skidl import *

U1 = Part("pdmlib", "RPi4-8GB", footprint="Connector_PinHeader_2.54mm:PinHeader_1x40_P2.54mm_Vertical", ref='U1')
U2 = Part("pdmlib", "ADXL345", footprint="Module:ADXL345", ref='U2')
U3 = Part("pdmlib", "MAX31865", footprint="Module:MAX31865", ref='U3')
U4 = Part("pdmlib", "INMP441", footprint="Module:INMP441", ref='U4')
R1 = Part("pdmlib", "PT100-M6", footprint="Module:PT100_M6", ref='R1')
C1 = Part("pdmlib", "100nF", footprint="Capacitor_SMD:C_0402_1005Metric", ref='C1')
C2 = Part("pdmlib", "100nF", footprint="Capacitor_SMD:C_0402_1005Metric", ref='C2')
C3 = Part("pdmlib", "100nF", footprint="Capacitor_SMD:C_0402_1005Metric", ref='C3')
C4 = Part("pdmlib", "10uF", footprint="Capacitor_SMD:CP_Elec_4x5.4", ref='C4')
R2 = Part("pdmlib", "10k", footprint="Resistor_SMD:R_0402_1005Metric", ref='R2')
R4 = Part("pdmlib", "330R", footprint="Resistor_SMD:R_0402_1005Metric", ref='R4')
D1 = Part("pdmlib", "LED", footprint="LED_SMD:LED_0603_1608Metric", ref='D1')
F1 = Part("pdmlib", "FAN-5V", footprint="Module:Fan_5V", ref='F1')

Net("3V3") += [U1["1"], U1["17"], U2["1"], U2["3"], U3["1"], U4["1"], C1["1"], C2["1"], C3["1"], C4["1"], R2["1"]]
Net("GND") += [U1["9"], U1["14"], U1["25"], U1["39"], U1["6"], U2["2"], U2["4"], U3["2"], U4["2"], U4["3"], C1["2"], C2["2"], C3["2"], C4["2"], D1["2"], F1["2"]]
Net("5V") += [U1["4"], F1["1"]]
Net("I2C_SDA") += [U1["3"], U2["5"]]
Net("I2C_SCL") += [U1["5"], U2["6"]]
Net("SPI_SCLK") += [U1["23"], U3["3"]]
Net("SPI_MOSI") += [U1["19"], U3["4"]]
Net("SPI_MISO") += [U3["5"], U1["21"]]
Net("SPI_CS0") += [U1["24"], U3["6"], R2["2"]]
Net("I2S_BCLK") += [U1["12"], U4["4"]]
Net("I2S_WS") += [U1["35"], U4["5"]]
Net("I2S_SD") += [U1["38"], U4["6"]]
Net("RTD_SENSE_P") += [R1["1"], U3["7"], U3["9"]]
Net("RTD_SENSE_N") += [R1["2"], U3["10"]]
Net("RTD_FORCE_N") += [R1["3"], U3["8"]]
Net("LED_A") += [U1["36"], R4["1"]]
Net("LED_K") += [R4["2"], D1["1"]]

ERC()
generate_netlist("pdm_rig.net")
