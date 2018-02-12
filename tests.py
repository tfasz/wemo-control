#!/usr/bin/python2

import datetime
import unittest
from control import *

appDir = os.path.dirname(os.path.realpath(sys.argv[0]))
jsonConfig = json.loads(open(appDir + '/config.json').read())
loc = Location(jsonConfig)

class TimeCalcTest(unittest.TestCase):
    def testDates(self):
        tMidnight = TimeCalc(jsonConfig, loc, datetime.datetime(2015, 9, 30, 0, 0, 0))
        tAlmostMidnight = TimeCalc(jsonConfig, loc, datetime.datetime(2015, 9, 30, 23, 59, 59))

class RuleTest(unittest.TestCase):
    def testRules(self):
        # Setup some times to calc 
        calcMidnight = TimeCalc(jsonConfig, loc, datetime.datetime(2015, 9, 30, 0, 0, 0))
        calcFiveThirty = TimeCalc(jsonConfig, loc, datetime.datetime(2015, 9, 30, 5, 30, 0))
        calcTen = TimeCalc(jsonConfig,loc, datetime.datetime(2015, 9, 30, 10, 0, 0))

        tEmptyRules = Device("emptyRule", calcMidnight, json.loads('{"rules":[]}'))
        self.assertFalse(tEmptyRules.expectedOn, "No rules - light is off")
        tOneRule = Device("oneRule", calcMidnight, json.loads('{"rules":[{"on":"5:00","off":"18:00"}]}'))
        self.assertFalse(tOneRule.expectedOn, "One rule at midnight - light is off")
        tTwoRules = Device("twoRules", calcMidnight, json.loads('{"rules":[{"on":"5:00","off":"18:00"},{"on":"8:00","off":"20:00"}]}'))
        self.assertFalse(tTwoRules.expectedOn, "Two rules at midnight - light is off")

        # Light should be ON at 5:30
        tOneRule = Device("oneRule", calcFiveThirty, json.loads('{"rules":[{"on":"5:00","off":"18:00"}]}'))
        self.assertTrue(tOneRule.expectedOn, "One rule at 5:30 - light is on")
        tTwoRules = Device("twoRules", calcFiveThirty, json.loads('{"rules":[{"on":"5:00","off":"18:00"},{"on":"8:00","off":"20:00"}]}'))
        self.assertTrue(tTwoRules.expectedOn, "Two rules at 5:30 - light is on")
        tTwoRules = Device("twoRules", calcTen, json.loads('{"rules":[{"on":"5:00","off":"18:00"},{"on":"8:00","off":"20:00"}]}'))
        self.assertTrue(tTwoRules.expectedOn, "Two rules at 10 - light is on")

        # Light should be ON even if time roles across midnight
        tOneRule = Device("oneRule", calcTen, json.loads('{"rules":[{"on":"5:00","off":"2:00"}]}'))
        self.assertTrue(tOneRule.expectedOn, "Over midnight rule at 10 - light is on")

# creating a new test suite
newSuite = unittest.TestSuite()
 
# adding a test case
newSuite.addTest(unittest.makeSuite(TimeCalcTest))
newSuite.addTest(unittest.makeSuite(RuleTest))

if __name__ == "__main__":
    unittest.main()
