# ////////////////////////////////////////////////////////////////
# //                     IMPORT STATEMENTS                      //
# ////////////////////////////////////////////////////////////////

import math
import sys
import time

from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import *
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.slider import Slider
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.clock import Clock
from kivy.animation import Animation
from functools import partial
from kivy.config import Config
from kivy.core.window import Window
from pidev.kivy import DPEAButton
from pidev.kivy import PauseScreen
from time import sleep
import RPi.GPIO as GPIO 
from pidev.stepper import stepper
from pidev.Cyprus_Commands import Cyprus_Commands_RPi as cyprus


# ////////////////////////////////////////////////////////////////
# //                      GLOBAL VARIABLES                      //
# //                         CONSTANTS                          //
# ////////////////////////////////////////////////////////////////
START = True
STOP = False
UP = False
DOWN = True
ON = True
OFF = False
YELLOW = .180, 0.188, 0.980, 1
BLUE = 0.917, 0.796, 0.380, 1
CLOCKWISE = 0
COUNTERCLOCKWISE = 1
ARM_SLEEP = 2.5
DEBOUNCE = 0.10

lowerTowerPosition = 60
upperTowerPosition = 76


# ////////////////////////////////////////////////////////////////
# //            DECLARE APP CLASS AND SCREENMANAGER             //
# //                     LOAD KIVY FILE                         //
# ////////////////////////////////////////////////////////////////
class MyApp(App):

    def build(self):
        self.title = "Robotic Arm"
        return sm

Builder.load_file('main.kv')
Window.clearcolor = (.1, .1,.1, 1) # (WHITE)

cyprus.open_spi()

# ////////////////////////////////////////////////////////////////
# //                    SLUSH/HARDWARE SETUP                    //
# ////////////////////////////////////////////////////////////////

sm = ScreenManager()
s0 = stepper(port=0, micro_steps=32, hold_current=20, run_current=20, accel_current=20, deaccel_current=20,
             steps_per_unit=200, speed = 2)

# ////////////////////////////////////////////////////////////////
# //                       MAIN FUNCTIONS                       //
# //             SHOULD INTERACT DIRECTLY WITH HARDWARE         //
# ////////////////////////////////////////////////////////////////
	
class MainScreen(Screen):
    version = cyprus.read_firmware_version()
    armPosition = 0
    lastClick = time.clock()
    towerStatus = 0

    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.initialize()

    def debounce(self):
        processInput = False
        currentTime = time.clock()
        if ((currentTime - self.lastClick) > DEBOUNCE):
            processInput = True
        self.lastClick = currentTime
        return processInput

    def toggleArm(self):
        print("Process arm movement here")
        if self.armControl.text == "Lower Arm":
            cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            self.armControl.text = "Raise Arm"
        else:
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            self.armControl.text = "Lower Arm"


    def toggleMagnet(self):
        print("Process magnet here")
        if self.magnetControl.text == "Hold Ball":
            sleep(0.5)
            cyprus.set_servo_position(2, 0)  # port 5 (0.5 not magnetized)
            self.magnetControl.text = "Drop Ball"
        else:
            sleep(0.5)
            cyprus.set_servo_position(2, 0.5)  # port 5 (0 magnet on)
            self.magnetControl.text = "Hold Ball"
        
    def auto(self):
        print("Run the arm automatically here")
        s0.go_until_press(0, 6400) #0 is the direction
        while s0.is_busy():
           sleep(.1)
        s0.go_to_position(.48) #go to tall tower
        while s0.is_busy():
           sleep(.1)
        sleep(1.5)
        self.isBallOnTallTower()
        sleep(.6)
        if self.towerStatus == 1:
            print("ball not on tall tower")
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            s0.go_to_position(.82)
            sleep(1.7)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            sleep(1.5)
            cyprus.set_servo_position(2, 0)
            sleep(0.1)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            sleep(0.7)
            s0.go_to_position(.48)
            while s0.is_busy():
                sleep(.1)
            sleep(1.9)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            sleep(0.7)
            cyprus.set_servo_position(2, 0.5)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
        else:
            print("moving the ball to short tower")
            cyprus.set_servo_position(2, 0)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            s0.go_to_position(.82)
            sleep(1.7)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            sleep(1.7)
            cyprus.set_servo_position(2, 0.5)
            cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
            sleep(0.5)
        self.initialize()

    def setArmPosition(self):
        print("Move arm here")
        s0.go_to_position(self.moveArm.value)
        self.armControlLabel.text = 'Arm Position: ' + str(self.moveArm.value)

    def homeArm(self):
        print("home the arm")
        #arm.home(self.homeDirection)
        s0.go_until_press(0, 6400)
        while s0.is_busy():
           sleep(.1)
        s0.set_as_home()
        
    def isBallOnTallTower(self):
        print("Determine if ball is on the top tower")
        cyprus.set_pwm_values(1, period_value=100000, compare_value=100000, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
        if (cyprus.read_gpio() & 0b0010):
            print("P7 is high")
            self.towerStatus = 1 #ball is not on the tall tower
        else: #if ball IS in tower
            print("went through else")
            self.towerStatus = 2


    def isBallOnShortTower(self):
        print("Determine if ball is on the bottom tower")
        
    def initialize(self):
        print("Home arm and turn off magnet")
        cyprus.set_pwm_values(1, period_value=100000, compare_value=0, compare_mode=cyprus.LESS_THAN_OR_EQUAL)
        cyprus.set_servo_position(2, 0.5)  # port 5
        self.homeArm()



    def resetColors(self):
        self.ids.armControl.color = YELLOW
        self.ids.magnetControl.color = YELLOW
        self.ids.autoo.color = BLUE

    def quit(self):
        MyApp().stop()
    
sm.add_widget(MainScreen(name = 'main'))


# ////////////////////////////////////////////////////////////////
# //                          RUN APP                           //
# ////////////////////////////////////////////////////////////////

MyApp().run()
cyprus.close_spi()
