#!/usr/bin/env python

from ouimeaux.environment import Environment

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

env = Environment(bridge_callback=on_bridge, with_cache=True)
env.start()

