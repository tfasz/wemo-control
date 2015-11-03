# wemo-control

Simple Python app that uses https://github.com/iancmcc/ouimeaux to control Wemo lights. The standard Belkin apps never seemed to work consistently and did not have all of the features I wanted (such as turning lights on earlier on cloudy days). 

## Features

For each light that you want to control you can setup rules in a JSON file. Rules can use fixed static times or be relative to sunrise and sunset. Because some days are darker and some days are lighter due to weather (aka clouds)
you can adjust and have lights come on earlier on cloudy days.

## Install

Make sure you have Python 2.x and `pip` installed. Install the dependencies and clone repo from GitHub.
```
sudo pip install pyephem
sudo pip install ouimeaux
git clone git@github.com:tfasz/wemo-control.git
```

## Configuration

Setup rules in `config.json` file in root directory.

```
cp config.json.example config.json
```

Edit location `lat` and `long` which controls sunrise/sunset times, set your `timezone`, and enter a weather API key to allow the app to lookup weather information at `http://openweathermap.org/api`.

### Rule Syntax

For each light, setup an array of rules. Make sure your light names match the keys under `lights`. You can view the names of your lights by running `wemo list` as described in the [documentation](http://ouimeaux.readthedocs.org/en/latest/). 

The simplest rules can have fixed `on` or `off` times describing the `HH:MM` that you want lights to come on. 

#### Sunrise/Sunset Relative Rules

To have a rule turn lights on relative to sunrise or sunset use `onSunrise` or `onSunset` and specifiy a value of the number of minutes you want the rule to be offset from sunrise/sunset. For example, to have a light turn on 45 minutes before sunset specity `"onSunset":-45` or 30 minutes after sunset specify `"onSunset":30`. Similarly you can turn lights off using `offSunset` and `offSunrise` rules.

#### Clouds

It can be useful to have lights stay on later in the morning or turn on earlier in the evening on dark cloudy days. The app queries the Open Weather Map API once per hour to get cloud data of 0-100 (0 is no clouds and 100 is full clouds). You can then specify a `onAdjustClouds` and `offAdjustClouds` value of minutes of adjustment you would like to adjust for clouds. For example, if you would like your lights to turn on 60 minutes earlier on really cloudy days specify `"onAdjustClouds":-60` - the math to adjust by is `onAdjustClouds*(cloudValue/100)`. On a mildly cloudy day this might turn on your lights 15-20 minutes earlier. On a fully sunny day it would not adjust at all.

## Run Schedule

Then schedule the app to run on some interval such as every 5 minutes by adding to your crontab.

```
# m h  dom mon dow   command
*/5 *  *   *   *     [PATH_TO_APP_FOLDER]/control.py
```
