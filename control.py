#!/usr/bin/python2

import datetime
import ephem                                  # install via: sudo pip install pyephem
import json
import os
import pytz
import sys
import time
from ouimeaux.environment import Environment  # install via: sudo pip install ouimeaux

os.environ['TZ'] = 'US/Pacific'
print(sys.version)

class TimeCalc:
    now = datetime.datetime.now()
    print "UTC now: " + str(now)
   
    pdt = pytz.timezone("US/Pacific")
    print "UTC offset: " + str(pdt.utcoffset(now))
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    todayOffset = today - pdt.utcoffset(now)
    o = ephem.Observer()
    o.date = ephem.Date(todayOffset)
    print "Ephem Date: " + str(o.date)
    o.lat = '47.561619'
    o.long = '-122.269219'
    sunrise = ephem.localtime(o.next_rising(ephem.Sun()))
    sunset = ephem.localtime(o.next_setting(ephem.Sun()))
    print "Sun up: " + str(sunrise) + " -> " + str(sunset)

    def parseTime(self, value):
        return time.strptime(value, "%H:%M")

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
        elif 'onSunset' in ruleConfig:
            self.timeOn = self.calc.getSunset(ruleConfig['onSunset'])
        elif 'onSunrise' in ruleConfig:
            self.timeOn = self.calc.getSunrise(ruleConfig['onSunrise'])

        if 'off' in ruleConfig:
            self.timeOff = self.calc.parseTime(ruleConfig['off']) 
        elif 'offSunrise' in ruleConfig:
            self.timeOff = self.calc.getSunset(ruleConfig['offSunrise'])
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
    lights = json.loads(open('rules.json').read())
    for name, lightConfig in lights.iteritems():
        print name, ":", lightConfig
        for ruleConfig in lightConfig['rules']:
            rule = Rule(ruleConfig)
            print rule


getRules()
