#!/usr/bin/python2

import calendar
import datetime
import ephem                                  # install via: sudo pip install pyephem
import json
import os
import pytz
import sys
import time
from ouimeaux.environment import Environment  # install via: sudo pip install ouimeaux

os.environ['TZ'] = 'US/Pacific'
#print(sys.version)

class TimeCalc:	
    pdt = pytz.timezone('US/Pacific') 
    o = ephem.Observer()
    o.lat = '47.561619'
    o.long = '-122.269219'

    def __init__(self, baseDate=None):
        if baseDate is None:
            baseDate = datetime.datetime.now()
        self.baseDate = self.floorMinute(baseDate)
        print("Base Date: " + str(self.baseDate))
        today = self.baseDate.replace(hour=0, minute=0)
        todayOffset = today - self.pdt.utcoffset(self.baseDate)
        self.o.date = ephem.Date(todayOffset)
        self.sunrise = self.floorMinute(ephem.localtime(self.o.next_rising(ephem.Sun())))
        self.sunset = self.floorMinute(ephem.localtime(self.o.next_setting(ephem.Sun())))
        print "Sun up: " + str(self.sunrise) + " -> " + str(self.sunset)
   
    def floorMinute(self, date):
        return date.replace(second=0, microsecond=0)

    def parseTime(self, value):
        dateVal = datetime.datetime.strptime(value, "%H:%M")
        return self.baseDate.replace(hour=dateVal.hour, minute=dateVal.minute)

    def getSunrise(self, offset):
        return self.sunrise + datetime.timedelta(minutes=offset) 

    def getSunset(self, offset):
        return self.sunset + datetime.timedelta(minutes=offset) 

class Light:
    def __init__(self):
        self.rules = []
        self.expectedState
        self.actualState

class Rule:
    calc = TimeCalc()

    def __init__(self, ruleConfig):
        if 'on' in ruleConfig:
            self.timeOn = self.calc.parseTime(ruleConfig['on']) 
        elif 'onSunrise' in ruleConfig:
            self.timeOn = self.calc.getSunrise(ruleConfig['onSunrise'])
        elif 'onSunset' in ruleConfig:
            self.timeOn = self.calc.getSunset(ruleConfig['onSunset'])

        if 'off' in ruleConfig:
            self.timeOff = self.calc.parseTime(ruleConfig['off']) 
        elif 'offSunrise' in ruleConfig:
            self.timeOff = self.calc.getSunrise(ruleConfig['offSunrise'])
        elif 'offSunset' in ruleConfig:
            self.timeOff = self.calc.getSunset(ruleConfig['offSunset'])

    def __str__(self):
        return "Rule from " + str(self.timeOn) + " -> " + str(self.timeOff) 

def on_switch(switch):
    print 'on switch' 

def on_bridge(bridge):
    print "Bridge:", bridge.name
    bridge.bridge_get_lights()
    for light in bridge.Lights:
        print "Light:", light
        if (light == "Living Room"):
            state = bridge.light_get_state(bridge.Lights[light])
            print "State:", state
            if (state['state'] == "1"):
                bridge.light_set_state(bridge.Lights[light],state="0",dim="0")
            else:
                bridge.light_set_state(bridge.Lights[light],state="1",dim="255")

#env = Environment(bridge_callback=on_bridge, with_cache=True)
#env.start()

def getRules():
    # Load our rule configuration
    lights = json.loads(open('rules.json').read())

    # Loop through the config settings for all of our lights
    for name, lightConfig in lights.iteritems():
        print name, ":", lightConfig

        # For each rule we want to calc our on/off times
        for ruleConfig in lightConfig['rules']:
            # Parse the ruleConfig for this rule
            rule = Rule(ruleConfig)
            print rule


getRules()
