#!/usr/bin/python2

import datetime
import unittest
from control import *

class TimeCalcTest(unittest.TestCase):
    def testDates(self):
        tMidnight = TimeCalc(datetime.datetime(2015, 9, 30, 0, 0, 0))
        tAlmostMidnight = TimeCalc(datetime.datetime(2015, 9, 30, 23, 59, 59))

class RuleTest(unittest.TestCase):
    def testRules(self):
        tEmptyRules = LightConfig(json.loads('{"emptyRules":{"rules":[]}}'))
        tOneRule = LightConfig(json.loads('{"oneRule":{"rules":[{"on":"5:00","off":"18:00"}]}}'))
        tTwoRules = LightConfig(json.loads('{"twoRules":{"rules":[{"on":"5:00","off":"18:00"},{"on":"8:00","off":"20:00"}]}}'))

# creating a new test suite
newSuite = unittest.TestSuite()
 
# adding a test case
newSuite.addTest(unittest.makeSuite(TimeCalcTest))
newSuite.addTest(unittest.makeSuite(RuleTest))

if __name__ == "__main__":
    unittest.main()
