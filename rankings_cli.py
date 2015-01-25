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
Usage: %s [options...]
Compute power rankings for head-to-head ESPN fantasy baseball leagues and
output the results as an HTML document.
The default action is to compute rankings for current matchup period.

Options:
    -h, --help          Print this usage message and quit
    -c <file>, --config=<file>  Configuration file to use (default: pr.conf)
    -w <week>, --week=<week>    Week number of the matchup period. Only one
                                -w or -s may be provided.
                                (Default: current week)
    -s, --season        Season power rankings to date. Only one of -w or -s may
                        be provided.
    -m, --post-message  Post a simple message to the league message board.
                        Pulls quotes from fortune if avaialble.
"""

from power_rankings import WeeklyRankings, SeasonRankings
import getopt
import datetime
import sys
import os
import subprocess


def readConfig(configFile):
    props = {}
    conf = open(configFile, 'r')
    for line in conf:
        if not line.startswith('#') and line.strip():
            prop = line.rstrip().split('=')
            props[prop[0]] = prop[1]

    return props


def printRankings(leagueName, teamAbbrMap, rankings,
                   seasonId, thisWeek):
    print("""\
<html>
<head>
  <title>%s %s - Week %s</title>
  <link rel="stylesheet" type="text/css" href="style.css">
</head>
<body>
  <h2>%s %s - Week %s Power Rankings</h2>

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
""" % (leagueName, seasonId, thisWeek, leagueName, seasonId, thisWeek))
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


def usage():
    print(__doc__ % sys.argv[0], file=sys.stderr)


def main():
    path = os.path.dirname(sys.argv[0])
    configFile = 'pr.conf'

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:w:smh',
                                   ['config=', 'week=', 'season',
                                    'post-message', 'help'])
    except getopt.GetoptError as err:
        print(str(err))
        usage()
        sys.exit(1)
    thisWeek = 0
    postMessageEnabled = False
    doWeek = False
    doSeason = False
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif o in ('-c', '--config'):
            configFile = a
        elif o in ('-w', '--week'):
            if doSeason:
                usage()
                sys.exit(1)
            else:
                try:
                    thisWeek = int(a)
                    doWeek = True
                except (TypeError, ValueError):
                    print('Error: Argument to -w must be a number',
                          file=sys.stderr)
                    usage()
                    sys.exit(1)
        elif o in ('-s', '--season'):
            if doWeek:
                usage()
                sys.exit(1)
            else:
                doSeason = True
        elif o == '-m':
            postMessageEnabled = True
        else:
            usage()
            sys.exit(1)

    if not doWeek and not doSeason:
        doWeek = True

    if not path == '':
        configFile = path + os.pathsep + configFile
    properties = readConfig(configFile)

    if doWeek and thisWeek <= 0:
        openingDay = datetime.date(int(properties['startYear']),
                                   int(properties['startMonth']),
                                   int(properties['startDate']))
        openingWeek = openingDay.isocalendar()[1]
        thisWeek = datetime.date.today().isocalendar()[1] - openingWeek - 1

    leagueId = properties['leagueId']
    seasonId = properties['seasonId']
    lowerBetter = properties['lowerBetter'].split(',')
    if doWeek:
        pr = WeeklyRankings(leagueId, seasonId, lowerBetter, thisWeek)
    else:
        pr = SeasonRankings(leagueId, seasonId, lowerBetter)

    pr.loginESPN(properties['username'], properties['password'])
    teamAbbrMap = pr.teamAbbreviations()
    rankings = pr.powerRankings()

    printRankings(properties['leagueName'], teamAbbrMap,
                  rankings, seasonId, thisWeek)
    printPowerMatrix(teamAbbrMap, rankings)

    if postMessageEnabled:
        if doWeek:
            subject = 'Week %d Power Rankings' % thisWeek
            period = 'week %d' % thisWeek
        else:
            subject = 'Season Power Rankings'
            period = 'the season so far'
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
    main()
