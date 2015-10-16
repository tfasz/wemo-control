# wemo-control

Simple Python app that uses https://github.com/iancmcc/ouimeaux to control Wemo lights. The standard Belkin apps never
seemed to work consistently and did not have all of the features I wanted (such as turning lights on earlier on cloudy days). 

## Features

For each light that you want to control you can setup rules in a JSON file. Rules can use fixed static times or be relative
to sunrise and sunset. Because some days are darker and some days are lighter due to weather (aka clouds)
you can adjust and have lights come on earlier on cloudy days.

## Configuration

Setup rules in `config.json` file in root directory.

```
cp config.json.example config.json
```

Edit location `lat` and 'long' which controls sunrise/sunset times. Setup a weather API key to allow
app to lookup cloud information (http://openweathermap.org/api).

Make sure your light names match the keys under `lights`. 

Then schedule the app to run on some interval such as every 5 minutes by adding to your crontab.

```
# m h  dom mon dow   command
*/5 *  *   *   *     [PATH_TO_APP_FOLDER]/control.py
```
