# The MIT License (MIT)
#
# Copyright (c) 2014 Michel Mansour
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


def printStandings(leagueName, teamAbbrMap, standings,
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
    for row in standings:
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


def printPowerMatrix(teamAbbrMap, standings):
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

    for row in sorted(standings, key=lambda x: teamAbbrMap[x['team']]):
        print('<tr>')
        print('\t<th><acronym title="%s">%s</acronym></th>' %
              (row['team'], teamAbbrMap[row['team']]))
        wins = row['wins']
        losses = row['losses']
        ties = row['ties']
        for opp in sorted(standings, key=lambda x: teamAbbrMap[x['team']]):
            if row['team'] == opp['team']:
                print('\t<td>&nbsp;</td>')
            else:
                oppName = opp['team']
                css = ''
                if ('opp' in row['powerRow'] and
                        row['powerRow']['opp'] == opp['team']):
                    css = 'matchup '
                oppWins = row['powerRow']['oppRecords'][oppName]['wins']
                oppLosses = row['powerRow']['oppRecords'][oppName]['losses']
                oppTies = row['powerRow']['oppRecords'][oppName]['ties']
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
    print("""\
Usage: %s [-c <file> | --config-file=<file>] [-w <week> | --week=<week> | -s |\
 --season] [-m | --post-message] [-h | --help]

    -h, --help                   Print this usage message and quit
    -c <file>, --config=<file>   Configuration file
    -w <week>, --week=<week>     Weekly power rankings for <week>
    -s, --season                 Season power rankings
    -m, --post-message           Post a message""" %
          sys.argv[0], file=sys.stderr)


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
        rankings = WeeklyRankings(leagueId, seasonId, lowerBetter, thisWeek)
    else:
        rankings = SeasonRankings(leagueId, seasonId, lowerBetter)

    rankings.loginESPN(properties['username'], properties['password'])
    teamAbbrMap = rankings.teamAbbreviations()
    standings = rankings.standings()

    printStandings(properties['leagueName'], teamAbbrMap,
                   standings, seasonId, thisWeek)
    printPowerMatrix(teamAbbrMap, standings)

    if postMessageEnabled:
        subject = 'test'
        (ret, fortune) = subprocess.getstatusoutput('fortune fortunes')
        # RANKINGS URL HERE
        msg = """Here are the power rankings for week %s: [link]%s[/link]

-- PowerBot""" % (thisWeek, properties['rankingsUrl'])
        if ret == 0:
            msg += """
[i]%s[/i]""" % fortune
        else:
            sys.stderr.write('fortune error')
        rankings.postMessage(thisWeek, msg)

if __name__ == '__main__':
    main()
