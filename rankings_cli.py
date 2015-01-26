#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The MIT License (MIT)
#
# Copyright (c) 2015 Michel Mansour
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""\
Compute power rankings for head-to-head ESPN fantasy baseball leagues and
output the results as an HTML document.
The default action is to compute rankings for current matchup period.
"""

from power_rankings import WeeklyRankings, SeasonRankings
import argparse
import datetime
import sys
import subprocess


def readConfig(configFile):
    props = {}
    with open(configFile, 'r') as conf:
        for line in conf:
            if not line.startswith('#') and line.strip():
                prop = line.rstrip().split('=')
                props[prop[0]] = prop[1]

    return props


def printRankings(leagueName, teamAbbrMap, rankings,
                  seasonId, thisWeek):
    if thisWeek > 0:
        rankingsTitle = 'Week %s' % thisWeek
        dateStr = ''
    else:
        rankingsTitle = 'Season'
        dateStr = '(%s)' % datetime.date.today().strftime('%x')
    print("""\
<html>
<head>
    <title>%(leagueName)s %(year)s - %(title)s</title>
  <link rel="stylesheet" type="text/css" href="style.css">
</head>
<body>
    <h2>%(leagueName)s %(year)s - %(title)s Power Rankings %(dateStr)s</h2>

  <h3>Power Rankings</h3>
    <table border="1">
      <tr>
        <th>Rank</th>
        <th>Team</th>
        <th>Record</th>
        <th>
          <acronym title="Aggregate Winning Percentage">AWP*</acronym>
        </th>
        <th>
          <acronym title="Opponent Aggregate Winning Percentage">OAWP**\
</acronym>
        </th>
      </tr>
""" % {'leagueName': leagueName, 'year': seasonId, 'title': rankingsTitle,
       'dateStr': dateStr})
    for row in rankings:
        awp = ('%.3f' % row['awp'])[1:]
        oppAwp = ('%.3f' % row['oppAwp'])[1:]
        print("""<tr><td>%d</td><td>%s (%s)</td><td>%d-%d-%d</td>\
<td>%s</td><td>%s</td></tr>""" %
              (row['rank'], row['team'], teamAbbrMap[row['team']],
               row['wins'], row['losses'], row['ties'],
               awp, oppAwp))
    print("""
    </table>

  <br/>""")


def printPowerMatrix(teamAbbrMap, rankings):
    print("""
  <h3>Relative Power Matrix</h3>
  <i>Actual matchup in <b>bold</b>.
  <br>
  <table border="1">
    <tr>
      <th>TEAM</th>""")

    for team in sorted(teamAbbrMap, key=teamAbbrMap.get):
        print("""      <th><acronym title="%s">%s</acronym></th>""" %
              (team, teamAbbrMap[team]))

    print("""      <th><acronym title="Aggregate Winning Percentage">AWP*\
</acronym></th>
    </tr>
""")

    for row in sorted(rankings, key=lambda x: teamAbbrMap[x['team']]):
        print('<tr>')
        print('\t<th><acronym title="%s">%s</acronym></th>' %
              (row['team'], teamAbbrMap[row['team']]))
        wins = row['wins']
        losses = row['losses']
        ties = row['ties']
        for opp in sorted(rankings, key=lambda x: teamAbbrMap[x['team']]):
            if row['team'] == opp['team']:
                print('\t<td>&nbsp;</td>')
            else:
                oppName = opp['team']
                css = ''
                if (row['matchupOpp'] == opp['team']):
                    css = 'matchup '
                oppWins = row['powerRow'][oppName]['wins']
                oppLosses = row['powerRow'][oppName]['losses']
                oppTies = row['powerRow'][oppName]['ties']
                if oppWins > oppLosses:
                    css += 'win'
                elif oppWins < oppLosses:
                    css += 'loss'
                else:
                    css += 'tie'
                print('\t<td class="%s">%d-%d-%d</td>' %
                      (css, oppWins, oppLosses, oppTies))
        awp = (wins + ties / 2.0) / (wins + losses + ties)
        awp = ('%.3f' % awp)[1:]
        print('\t<td class="total">%d-%d-%d (%s)</td>' %
              (wins, losses, ties, awp))
        print('</tr>')

    print("""\
</table>
  <br>
  * <i><b>Aggregate Winning Percentage (AWP)</b> - A team's combined record \
against every other team for the week.</i>
  <br>
  ** <i><b>Opponent Aggregate Winning Percentage (OAWP)</b> - Average AWP of \
all opponents to date.</i>
  <br /><br />
  <a href="../rankings">Other Weeks</a>
</body>
</html>
""")


def main(args):
    thisWeek = 0
    doSeason = False
    properties = readConfig(args.config)

    # Determine the rankings period
    if args.season:
        doSeason = True
    else:
        thisWeek = args.week
        if thisWeek <= 0:
            openingDay = datetime.date(int(properties['startYear']),
                                       int(properties['startMonth']),
                                       int(properties['startDate']))
            openingWeek = openingDay.isocalendar()[1]
            thisWeek = datetime.date.today().isocalendar()[1] - openingWeek - 1

    leagueId = properties['leagueId']
    seasonId = properties['seasonId']
    lowerBetter = properties['lowerBetter'].split(',')
    if doSeason:
        pr = SeasonRankings(leagueId, seasonId, lowerBetter)
    else:
        pr = WeeklyRankings(leagueId, seasonId, lowerBetter, thisWeek)

    pr.loginESPN(properties['username'], properties['password'])
    teamAbbrMap = pr.teamAbbreviations()
    rankings = pr.powerRankings()

    printRankings(properties['leagueName'], teamAbbrMap,
                  rankings, seasonId, thisWeek)
    printPowerMatrix(teamAbbrMap, rankings)

    # Post a message if requested
    if args.postMessage:
        if doSeason:
            subject = 'Season Power Rankings'
            period = 'the season so far'
        else:
            subject = 'Week %d Power Rankings' % thisWeek
            period = 'week %d' % thisWeek
        (ret, fortune) = subprocess.getstatusoutput('fortune fortunes')
        # RANKINGS URL HERE
        msg = """Here are the power rankings for %s: [link]%s[/link]

-- PowerBot""" % (period, properties['rankingsUrl'])
        if ret == 0:
            msg += """
[i]%s[/i]""" % fortune
        else:
            sys.stderr.write('fortune error')
        pr.postMessage(msg, subject)

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-c', '--config', default='pr.conf',
                        help='configuration file to use')
    matchupPeriodGroup = parser.add_mutually_exclusive_group()
    matchupPeriodGroup.add_argument('-w', '--week', type=int, default=-1,
                                    help='compute rankings for WEEK')
    matchupPeriodGroup.add_argument('-s', '--season', action='store_true',
                                    help='compute rankings for the season \
                                    so far')
    parser.add_argument('-m', '--post-message', dest='postMessage',
                        action='store_true',
                        help='post to the league message board')

    args = parser.parse_args()
    main(args)
