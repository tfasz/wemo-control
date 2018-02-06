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
app_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
log_format = logging.Formatter('%(asctime)s: %(message)s')
log = logging.getLogger('control')
log.setLevel(logging.DEBUG)
log_file = logging.handlers.RotatingFileHandler(app_dir + '/logs/control.log', maxBytes=100000, backupCount=5)
log_file.setFormatter(log_format)
log.addHandler(log_file)

change_log = logging.getLogger('control-changes')
change_log.setLevel(logging.INFO)
log_file = logging.FileHandler(app_dir + '/logs/control-changes.log')
log_file.setFormatter(log_format)
change_log.addHandler(log_file)

# Location information
class Location:
    def __init__(self, json_config):
        self.tz = pytz.timezone(json_config['timezone']) 
        self.lat = json_config['location']['lat']
        self.long = json_config['location']['long']
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
    def __init__(self, json_config, location):
       self.apiKey = json_config['weatherApiKey']
       weather_json = None
       weather_cache_file = app_dir + '/cache/weather.json'
       if os.path.isfile(weather_cache_file):
           if os.path.getmtime(weather_cache_file) > time.time() - 3600:
               log.debug("Loading weather data from cache")
               weather_json = json.loads(open(weather_cache_file).read())
                
       if weather_json == None:
           log.debug("Loading weather data from URL")
           # Fetch from the URL and save to our cache file
           try:
               r = urllib2.urlopen("http://api.openweathermap.org/data/2.5/weather?APPID=" + self.apiKey + "&lat=" + location.lat + "&lon=" + location.long)
               weather_json= json.load(r)
               with open(weather_cache_file, 'w') as fp:
                   json.dump(weather_json, fp)
           except:
               log.warn("Error fetching weather JSON from URL")

       if weather_json != None and 'clouds' in weather_json and 'all' in weather_json['clouds']:
           self.clouds = weather_json['clouds']['all']
       else:
           self.clouds = 0
       log.debug("Found cloud data: " + str(self.clouds))

# Keep track of prior state so we can tell if manually overwritten
class SavedState:
    def __init__(self):
       self.cache_file = app_dir + '/cache/state.json'
       self.state = {}
       if os.path.isfile(self.cache_file):
           log.debug("Loading state data from cache")
           self.state = json.loads(open(self.cache_file).read())
                
    def save(self):
        with open(self.cache_file, 'w') as fp:
            json.dump(self.state, fp)

    def set(self, device_name, state):
        self.state[device_name] = state

# Logic to normalize times in our rules to datetimes. This is both dealing
# with calculating sunrise/sunsite (+/- offsets) and for parsing HH:MM times.
#
# Notes:
#  - does not currently handle sunrise/sunset calc when they cross midnight
#    - this is to handle scenario where the sunrise/sunset cross over the
#      other fixed time and we currently disable the rule
#
class TimeCalc:	
    def __init__(self, json_config, location, baseDate=None):
        if baseDate is None:
            baseDate = datetime.datetime.now()
        self.baseDate = self.floorMinute(baseDate)
        log.debug("Base Date: " + str(self.baseDate))
        locDate = LocationDate(location, self.baseDate)
        self.sunrise = self.floorMinute(locDate.sunrise)
        self.sunset = self.floorMinute(locDate.sunset)
        log.debug("Sun up: " + str(self.sunrise) + " -> " + str(self.sunset))
  
        # Load our weather too
        self.weather = Weather(json_config, location)

    def isWeekend(self):
        return self.baseDate.weekday() >= 5
 
   # Check if this is a specific day of the week - 0 for Monday thru 6 for Sunday
    def isDayOfWeek(self, daysOfWeek):
        return str(self.baseDate.weekday()) in daysOfWeek
  
    def floorMinute(self, date):
        return date.replace(second=0, microsecond=0)

    def parseTime(self, value):
        dateVal = datetime.datetime.strptime(value, "%H:%M")
        return self.baseDate.replace(hour=dateVal.hour, minute=dateVal.minute)

    def getSunrise(self, offset, adjustClouds):
        sunrise = self.sunrise + datetime.timedelta(minutes=offset) 
        return self.adjustForClouds(sunrise, adjustClouds)

    def getSunset(self, offset, adjustClouds):
        sunset = self.sunset + datetime.timedelta(minutes=offset) 
        return self.adjustForClouds(sunset, adjustClouds)

    def adjustForClouds(self, time, adjustClouds):
        if adjustClouds == 0 or self.weather.clouds <= 0 or self.weather.clouds > 100:
            return time
        adjustment = adjustClouds * (self.weather.clouds/100.0)
        adjustedTime = time + datetime.timedelta(minutes=adjustment)
        log.debug("Adjusting time for clouds by " + str(adjustment) + " minutes from " + str(time) + " to " + str(adjustedTime))
        return adjustedTime

    def active(self, timeOn, timeOff):
        return (timeOn <= self.baseDate and timeOff > self.baseDate)

class Rule:
    def __init__(self, calc, rule_config):
        # If we have specific on/off times (no sunrise/sunset) we can let rules cross midnight.
        # Otherwise we currently assume rules have to be within a day.
        self.timeOnExact = False
        self.timeOffExact = False
 
        # If this rule is only good for certain days of the week check - apply check
        # Monday=0 thru Sunday=6
        if 'daysOfWeek' in rule_config and rule_config['daysOfWeek']:
            if not calc.isDayOfWeek(rule_config['daysOfWeek']):
                self.enabled = False
                return
            else:
                log.debug("Day of week rule passed")

        # See if we have any weather adjustment for clouds - these only apply
        # for sunrise/sunset rules. 
        onAdjustClouds = 0
        offAdjustClouds = 0
        if 'onAdjustClouds' in rule_config:
            onAdjustClouds = rule_config['onAdjustClouds']
        if 'offAdjustClouds' in rule_config:
            offAdjustClouds = rule_config['offAdjustClouds']

        if 'on' in rule_config:
            self.timeOn = calc.parseTime(rule_config['on']) 
            self.timeOnExact = True
        elif 'onSunrise' in rule_config:
            self.timeOn = calc.getSunrise(rule_config['onSunrise'], onAdjustClouds)
        elif 'onSunset' in rule_config:
            self.timeOn = calc.getSunset(rule_config['onSunset'], onAdjustClouds)

        if 'off' in rule_config:
            self.timeOff = calc.parseTime(rule_config['off']) 
            self.timeOffExact = True
        elif 'offSunrise' in rule_config:
            self.timeOff = calc.getSunrise(rule_config['offSunrise'], offAdjustClouds)
        elif 'offSunset' in rule_config:
            self.timeOff = calc.getSunset(rule_config['offSunset'], offAdjustClouds)

        # If we have exact on and off times we assume it can roll across midnight
        if self.timeOnExact and self.timeOffExact:
            if self.timeOff < self.timeOn:
                self.timeOff = self.timeOff + datetime.timedelta(days=1)

        # Decide if this rule is currently on/off
        self.enabled = calc.active(self.timeOn, self.timeOff)

    def __str__(self):
        try:
            return "Rule from " + str(self.timeOn) + " -> " + str(self.timeOff) + " Enabled: " + str(self.enabled)
        except:
            pass
        return "Rule Enabled: " + str(self.enabled)

class Device:
    def __init__(self, name, calc, config):
        self.name = name;
        self.expectedOn = False

        # For each rule we want to calc our on/off times
        self.rules = []
        for rule_config in config['rules']:
            # Parse the rule_config for this rule
            rule = Rule(calc, rule_config)
            log.debug(rule)
            self.rules.append(rule)

            # Light should be ON if any rule is enabled
            if rule.enabled:
                self.expectedOn = True

    def __str__(self):
        return "Device " + self.name + " - expectedOn: " + str(self.expectedOn) 

# Parse our configuration file
class WemoConfig:
    def __init__(self, json_config):
        self.location = Location(json_config)
        self.calc = TimeCalc(json_config, self.location)
        self.saved_state = SavedState()
        self.switches = {}
        self.lights = {}

        # Loop through the config settings for all of our switches
        for name, config in json_config['switches'].iteritems():
            # Lowercase light name so our check is case insensitive
            name = name.lower()
            device = Device(name, self.calc, config)
            self.switches[name] = device
            log.debug(device)

        for name, config in json_config['lights'].iteritems():
            # Lowercase light name so our check is case insensitive
            name = name.lower()
            device = Device(name, self.calc, config)
            self.lights[name] = device
            log.debug(device)

    def save(self):
        self.saved_state.save()

class WemoControl:
    def __init__(self, wemo_config):
        self.wemo_config = wemo_config

    def process(self):
        try:
            self.env = Environment(switch_callback=self.on_switch, bridge_callback=self.on_bridge, with_subscribers=False)
            self.env.start()
            self.env.discover(10)
        except Exception, e:
            log.exception("Failed to start environment.")

    def fadeOn(self, bridge, light):
        state = bridge.light_get_state(bridge.Lights[light])
        if state['state'] == "0":
            log.debug("Fading light " + light + " to ON")
            bridge.light_set_state(bridge.Lights[light], dim="255", transition_duration="100")
            time.sleep(10)
        log.debug("Setting light " + light + " to ON")
        bridge.light_set_state(bridge.Lights[light], state="1")
                
    def fadeOff(self, bridge, light):
        state = bridge.light_get_state(bridge.Lights[light])
        if state['state'] == "1":
            log.debug("Fading light " + light + " to OFF")
            bridge.light_set_state(bridge.Lights[light], dim="0", transition_duration="100")
            time.sleep(10)
        log.debug("Setting light " + light + " to OFF")
        bridge.light_set_state(bridge.Lights[light], state="0")
                
    def on_switch(self, switch):
        log.debug("Found switch: " + str(switch))
        switch_name = switch.name.lower()
        if switch_name in self.wemo_config.switches:
            log.debug("Found config for switch: " + switch_name)
            switch_config = self.wemo_config.switches[switch_name]
            state = switch.get_state(force_update=True)
            log.debug("Current state: " + str(state) + ", Expected State: " + str(switch_config.expectedOn))
            if state == 1 and not switch_config.expectedOn:
                log.debug("Turning switch OFF")
                change_log.info(switch.name + " -> OFF")
                switch.set_state(switch_config.expectedOn)
                self.wemo_config.saved_state.set(switch.name, 0)
            elif state == 0 and switch_config.expectedOn:
                log.debug("Turning switch ON")
                change_log.info(switch.name + " -> ON")
                switch.set_state(switch_config.expectedOn)
                self.wemo_config.saved_state.set(switch.name, 1)

    def on_bridge(self, bridge):
        bridge.bridge_get_lights()
        log.debug("Found lights: " + str(bridge.Lights))
        for light in bridge.Lights:
            light = light.lower()
            log.debug("Looking for config for light: " + light)
            if light in self.wemo_config.lights:
                log.debug("Found config for light: " + light)
                lightConfig = self.wemo_config.lights[light]
                state = bridge.light_get_state(bridge.Lights[light])

                # Log a message based on the current state
                log.debug("Current state: " + str(state) + ", Expected State: " + str(lightConfig.expectedOn))
                if state['state'] == "1" and not lightConfig.expectedOn:
                    change_log.info(light + " -> OFF")
                elif state['state'] == "0" and lightConfig.expectedOn:
                    change_log.info(light + " -> ON")

                # Because the light state can get out of sync with manual on/off changes just set the state
                # every time - even if we think it is already the correct state.
                if lightConfig.expectedOn:
                    self.fadeOn(bridge, light)
                else:
                    self.fadeOff(bridge, light)

# Run main if executed directly
if __name__ == '__main__':
    log.info("**** controlLights: Starting ****")
    wemo_config = WemoConfig(json.loads(open(app_dir + '/config.json').read()))
    log.info("**** controlLights: Loaded config - Setting Light Status ****")
    wemo_control = WemoControl(wemo_config)
    wemo_control.process()
    wemo_config.save()
    log.info("**** controlLights: Complete ****")
