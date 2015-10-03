#!/usr/bin/python2

import datetime
import unittest
from control import *

loc = Location(json.loads('{"timezone":"US/Pacific","location":{"lat":"47.56","long":"-122.26"}}'))

class TimeCalcTest(unittest.TestCase):
    def testDates(self):
        tMidnight = TimeCalc(loc, datetime.datetime(2015, 9, 30, 0, 0, 0))
        tAlmostMidnight = TimeCalc(loc, datetime.datetime(2015, 9, 30, 23, 59, 59))

class RuleTest(unittest.TestCase):
    def testRules(self):
        # Setup some times to calc 
        calcMidnight = TimeCalc(loc, datetime.datetime(2015, 9, 30, 0, 0, 0))
        calcFiveThirty = TimeCalc(loc, datetime.datetime(2015, 9, 30, 5, 30, 0))
        calcTen = TimeCalc(loc, datetime.datetime(2015, 9, 30, 10, 0, 0))

        tEmptyRules = Light("emptyRule", calcMidnight, json.loads('{"rules":[]}'))
        self.assertFalse(tEmptyRules.expectedOn, "No rules - light is off")
        tOneRule = Light("oneRule", calcMidnight, json.loads('{"rules":[{"on":"5:00","off":"18:00"}]}'))
        self.assertFalse(tOneRule.expectedOn, "One rule at midnight - light is off")
        tTwoRules = Light("twoRules", calcMidnight, json.loads('{"rules":[{"on":"5:00","off":"18:00"},{"on":"8:00","off":"20:00"}]}'))
        self.assertFalse(tTwoRules.expectedOn, "Two rules at midnight - light is off")

        # Light should be ON at 5:30
        tOneRule = Light("oneRule", calcFiveThirty, json.loads('{"rules":[{"on":"5:00","off":"18:00"}]}'))
        self.assertTrue(tOneRule.expectedOn, "One rule at 5:30 - light is on")
        tTwoRules = Light("twoRules", calcFiveThirty, json.loads('{"rules":[{"on":"5:00","off":"18:00"},{"on":"8:00","off":"20:00"}]}'))
        self.assertTrue(tTwoRules.expectedOn, "Two rules at 5:30 - light is on")
        tTwoRules = Light("twoRules", calcTen, json.loads('{"rules":[{"on":"5:00","off":"18:00"},{"on":"8:00","off":"20:00"}]}'))
        self.assertTrue(tTwoRules.expectedOn, "Two rules at 10 - light is on")

# creating a new test suite
newSuite = unittest.TestSuite()
 
# adding a test case
newSuite.addTest(unittest.makeSuite(TimeCalcTest))
newSuite.addTest(unittest.makeSuite(RuleTest))

if __name__ == "__main__":
    unittest.main()
