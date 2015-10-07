#!/usr/bin/python2

import calendar
import datetime
import ephem                                  # install via: sudo pip install pyephem
import logging
import logging.handlers
import json
import os
import pytz
import sys
import time
import urllib2
from ouimeaux.environment import Environment  # install via: sudo pip install ouimeaux

# Logging
appDir = os.path.dirname(os.path.realpath(sys.argv[0]))
log = logging.getLogger('control')
log.setLevel(logging.DEBUG)
log.addHandler(logging.handlers.RotatingFileHandler(appDir + '/control.log', maxBytes=100000, backupCount=5))

changeLog = logging.getLogger('control-changes')
changeLog.setLevel(logging.INFO)
logFormat = logging.Formatter('%(asctime)s: %(message)s')
logFile = logging.FileHandler(appDir + '/control-changes.log')
logFile.setFormatter(logFormat)
changeLog.addHandler(logFile)

# Location information
class Location:
    def __init__(self, jsonConfig):
        self.tz = pytz.timezone(jsonConfig['timezone']) 
        self.lat = jsonConfig['location']['lat']
        self.long = jsonConfig['location']['long']
        os.environ['TZ'] = 'US/Pacific'

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

# Start testing weather logic - can we turn on earlier when cloudy
class Weather:
    def __init__(self, location):
       weatherJson = None
       weatherCacheFile = appDir + '/weather.json'
       if os.path.isfile(weatherCacheFile) and os.path.getmtime(weatherCacheFile) > time.time() - 60000:
           log.debug("Loading weather data from cache")
           weatherJson = json.loads(open(weatherCacheFile).read())
                
       if weatherJson == None:
           log.debug("Loading weather data from URL")
           # Fetch from the URL and save to our cache file
           r = urllib2.urlopen("http://api.openweathermap.org/data/2.5/weather?lat=" + location.lat + "&lon=" + location.long)
           weatherJson = json.load(r)
           with open(weatherCacheFile, 'w') as fp:
               json.dump(weatherJson, fp)

       if 'clouds' in weatherJson and 'all' in weatherJson['clouds']:
           log.debug("Clouds: " + str(weatherJson['clouds']['all']))

# Logic to normalize times in our rules to datetimes. This is both dealing
# with calculating sunrise/sunsite (+/- offsets) and for parsing HH:MM times.
#
# Notes:
#  - does not currently handle sunrise/sunset calc
#
#
class TimeCalc:	
    def __init__(self, location, baseDate=None):
        if baseDate is None:
            baseDate = datetime.datetime.now()
        self.baseDate = self.floorMinute(baseDate)
        log.debug("Base Date: " + str(self.baseDate))
        locDate = LocationDate(location, self.baseDate)
        self.sunrise = self.floorMinute(locDate.sunrise)
        self.sunset = self.floorMinute(locDate.sunset)
        log.debug("Sun up: " + str(self.sunrise) + " -> " + str(self.sunset))
  
        # Load our weather too
        weather = Weather(location)
 
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
        self.timeOnExact = False
        self.timeOffExact = False
 
        if 'on' in ruleConfig:
            self.timeOn = calc.parseTime(ruleConfig['on']) 
            self.timeOnExact = True
        elif 'onSunrise' in ruleConfig:
            self.timeOn = calc.getSunrise(ruleConfig['onSunrise'])
        elif 'onSunset' in ruleConfig:
            self.timeOn = calc.getSunset(ruleConfig['onSunset'])

        if 'off' in ruleConfig:
            self.timeOff = calc.parseTime(ruleConfig['off']) 
            self.timeOffExact = True
        elif 'offSunrise' in ruleConfig:
            self.timeOff = calc.getSunrise(ruleConfig['offSunrise'])
        elif 'offSunset' in ruleConfig:
            self.timeOff = calc.getSunset(ruleConfig['offSunset'])

        # If we have exact on and off times we assume it can roll across midnight
        if self.timeOnExact and self.timeOffExact:
            if self.timeOff < self.timeOn:
                self.timeOff = self.timeOff + datetime.timedelta(days=1)

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
            log.debug(rule)
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
        self.lights = {}
        # Loop through the config settings for all of our lights
        for name, lightConfig in jsonConfig['lights'].iteritems():
            light = Light(name, self.calc, lightConfig)
            self.lights[name] = light
            log.debug(light)

class WemoControl:
    def __init__(self, wemoConfig):
        self.wemoConfig = wemoConfig

    def process(self):
        self.env = Environment(bridge_callback=self.on_bridge, with_cache=True)
        self.env.start()

    def on_switch(self, switch):
        log.debug("on_switch")
    
    def on_bridge(self, bridge):
        bridge.bridge_get_lights()
        for light in bridge.Lights:
            log.debug("Looking for config for light" + light)
            if light in self.wemoConfig.lights:
                lightConfig = self.wemoConfig.lights[light]
                state = bridge.light_get_state(bridge.Lights[light])
                log.debug("Current state:" + str(state) + ", Expected State:" + str(lightConfig.expectedOn))
                if state['state'] == "1" and lightConfig.expectedOn == False:
                    changeLog.info("Turning " + light + " light off")
                    bridge.light_set_state(bridge.Lights[light],state="0",dim="0")
                elif state['state'] == "0" and lightConfig.expectedOn == True:
                    changeLog.info("Turning " + light + " light on")
                    bridge.light_set_state(bridge.Lights[light],state="1",dim="255")

def controlLights():
    # Parse rules into lights
    log.debug("Starting controlLights")
    wemoConfig = WemoConfig(json.loads(open(appDir + '/rules.json').read()))
    wemoControl = WemoControl(wemoConfig)
    wemoControl.process()
    log.debug("complete")

# Run main if executed directly
if __name__ == '__main__':
    controlLights()
