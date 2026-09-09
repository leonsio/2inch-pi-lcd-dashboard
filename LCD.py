#!/usr/bin/python
# -*- coding: UTF-8 -*-
#import chardet
import os
import sys 
import time
import logging
import spidev as SPI
sys.path.append("..")

from lcd import LCD_2inch
from PIL import Image, ImageDraw, ImageFont

# Raspberry Pi pin configuration:
RST = 22
DC = 25
BL = 23
bus = 0 
device = 0 
logging.basicConfig(level=logging.DEBUG)
try:
    # display with hardware SPI:
    ''' Warning!!!Don't  creation of multiple displayer objects!!! '''
    #disp = LCD_2inch.LCD_2inch(spi=SPI.SpiDev(bus, device),spi_freq=10000000,rst=RST,dc=DC,bl=BL)
    disp = LCD_2inch.LCD_2inch()
    # Initialize library.
    disp.Init()
    # Clear display.
    disp.clear()
    #Set the backlight to 100
    disp.bl_DutyCycle(50)

    # Create blank image for drawing.
    image1 = Image.new("RGB", (disp.height, disp.width ), "WHITE")
    draw = ImageDraw.Draw(image1)

    logging.info("draw text")
    Font1 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 35)
    Font2 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 25)
    Font3 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 20)
    Font4 = ImageFont.truetype("./font/JetBrainsMono-Medium.ttf", 15)

    draw.text((1, 1), 'A', fill = "BLACK",font=Font1)
    draw.text((300, 1), 'A', fill = "BLACK",font=Font1)
    draw.text((1, 210), 'A', fill = "BLACK",font=Font1)
    draw.text((300, 210), 'A', fill = "BLACK",font=Font1)

    # Draw vertical lines
    draw.line([((320 / 3) * 1 , 0), ((320 / 3) * 1, 240)], fill="BLACK", width=2, joint=None)
    draw.line([((320 / 3) * 2 , 0), ((320 / 3) * 2, 240)], fill="BLACK", width=2, joint=None)

    # Draw horizontal lines
    draw.line([(0, (240 / 3) * 1), (320, (240 / 3) * 1)], fill="BLACK", width=2, joint=None)
    draw.line([(0, (240 / 3) * 2), (320, (240 / 3) * 2)], fill="BLACK", width=2, joint=None)
    time.sleep(3)

    draw.text((1, 1), 'B', fill = "BLACK",font=Font1)

    time.sleep(3)
    disp.module_exit()
    logging.info("quit:")
except IOError as e:
    logging.info(e)    
except KeyboardInterrupt:
    disp.module_exit()
    logging.info("quit:")
    exit()
