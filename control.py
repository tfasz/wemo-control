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

# Location information
class Location:
    def __init__(self, jsonConfig):
        self.tz = pytz.timezone(jsonConfig['timezone']) 
        self.lat = jsonConfig['location']['lat']
        self.long = jsonConfig['location']['long']

# Information about a location at a specific date - namely the sunrise and sunset times
# in the local timezone.
class LocationDate:
    def __init__(self, location, date):
        self.date = date
        self.today = self.date.replace(hour=0, minute=0)
        self.tzOffset = self.today - location.tz.utcoffset(self.today)
        self.obs = ephem.Observer()
        self.obs.lat = location.lat 
        self.obs.long = location.long 
        self.obs.date = ephem.Date(self.tzOffset)
        self.sunrise = ephem.localtime(self.obs.next_rising(ephem.Sun()))
        self.sunset = ephem.localtime(self.obs.next_setting(ephem.Sun()))

# Logic to normalize times in our rules to datetimes. This is both dealing
# with calculating sunrise/sunsite (+/- offsets) and for parsing HH:MM times.
class TimeCalc:	
    def __init__(self, location, baseDate=None):
        if baseDate is None:
            baseDate = datetime.datetime.now()
        self.baseDate = self.floorMinute(baseDate)
        print("Base Date: " + str(self.baseDate))
        locDate = LocationDate(location, self.baseDate)
        self.sunrise = self.floorMinute(locDate.sunrise)
        self.sunset = self.floorMinute(locDate.sunset)
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

    def active(self, timeOn, timeOff):
        return (timeOn <= self.baseDate and timeOff > self.baseDate)

class Rule:

    def __init__(self, calc, ruleConfig):
        if 'on' in ruleConfig:
            self.timeOn = calc.parseTime(ruleConfig['on']) 
        elif 'onSunrise' in ruleConfig:
            self.timeOn = calc.getSunrise(ruleConfig['onSunrise'])
        elif 'onSunset' in ruleConfig:
            self.timeOn = calc.getSunset(ruleConfig['onSunset'])

        if 'off' in ruleConfig:
            self.timeOff = calc.parseTime(ruleConfig['off']) 
        elif 'offSunrise' in ruleConfig:
            self.timeOff = calc.getSunrise(ruleConfig['offSunrise'])
        elif 'offSunset' in ruleConfig:
            self.timeOff = calc.getSunset(ruleConfig['offSunset'])

        # Decide if this rule is currently on/off
        self.enabled = calc.active(self.timeOn, self.timeOff)

    def __str__(self):
        return "Rule from " + str(self.timeOn) + " -> " + str(self.timeOff) + "  Enabled: " + str(self.enabled)

class Light:
    def __init__(self, name, calc, config):
        self.name = name;
        self.expectedOn = False

        # For each rule we want to calc our on/off times
        self.rules = []
        for ruleConfig in config['rules']:
            # Parse the ruleConfig for this rule
            rule = Rule(calc, ruleConfig)
            print rule
            self.rules.append(rule)

            # Light should be ON if any rule is enabled
            if rule.enabled:
                self.expectedOn = True

    def __str__(self):
        return "Light " + self.name + " - expectedOn: " + str(self.expectedOn) 

class WemoConfig:

    def __init__(self, jsonConfig):
        self.location = Location(jsonConfig)
        self.calc = TimeCalc(self.location)
        # Loop through the config settings for all of our lights
        for name, lightConfig in jsonConfig['lights'].iteritems():
            light = Light(name, self.calc, lightConfig)
            print light


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
    # Parse rules into lights
    wemoConfig = WemoConfig(json.loads(open('rules.json').read()))

# Run main if executed directly
if __name__ == '__main__':
    getRules()
