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

import pycurl
from bs4 import BeautifulSoup
import io
import re
import datetime
import getopt
import sys, os, subprocess

def readConfig(configFile):
    props = {}
    conf = open(configFile, 'r')
    for line in conf:
        if not line.startswith('#') and line.strip():
            prop = line.rstrip().split('=')
            props[prop[0]] = prop[1]

    return props

def loginESPN(curl, cookieFile, leagueId, username, password):
    fp = open('/dev/null', 'wb')

    curl.setopt(pycurl.WRITEDATA, fp)
    curl.setopt(pycurl.URL, "https://r.espn.go.com/espn/fantasy/login")
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.COOKIEFILE, cookieFile)
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.POSTFIELDS, "failedAttempts=2&SUBMIT=1&failedLocation=http://games.espn.go.com/flb/signin?redir=http%%3A%%2F%%2Fgames.espn.go.com%%2Fflb%%2Fstandings%%3FleagueId%%3D%s%%26e=1%%26aff_code=espn_fantgames&appRedirect=http://games.espn.go.com/flb/standings?leagueId=%s&cookieDomain=.go.com&multipleDomains=true&username=%s&password=%s&submit=Sign+In" % (leagueId, leagueId, username, password))
    curl.perform()

def postMessage(curl, cookieFile, leagueId, thisWeek, message, subject=''):
    if subject == '':
        subject = 'Power Rankings: Week %s' % thisWeek
    curl.setopt(pycurl.URL, 'http://games.espn.go.com/flb/tools/postmessage?leagueId=%s&typeId=0&topicId=0' % properties['leagueId'])
    curl.setopt(pycurl.COOKIEFILE, cookieFile)
    curl.setopt(pycurl.POST, 1)
    curl.setopt(pycurl.POSTFIELDS, 'subject=%s&body=%s&btnSubmit=Submit+Message&typeId=0&topicId=0&redir=/flb/leagueoffice?leagueId=%s&incoming=1' % (subject, message, leagueId))
    curl.perform()

def getTeamAbbreviations(curl, cookieFile, leagueId, seasonId):
    teamAbbrMap = {}

    b = io.BytesIO()
    curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/leaguesetup/ownerinfo?leagueId=%s&seasonId=%s" % (leagueId, seasonId))
    curl.setopt(pycurl.WRITEFUNCTION, b.write)
    curl.setopt(pycurl.COOKIEFILE, cookieFile)
    curl.perform()
    soup = BeautifulSoup(b.getvalue())
    b.close()
    ownerRows = soup.findAll("tr", "ownerRow")
    for row in ownerRows:
        cells = row.findAll("td")
        if re.compile("[0-9]+").match(str(cells[0].contents[0])):
            abbr = cells[1].contents[0]
            teamName = cells[2].findAll('a')[0].contents[0];
            teamAbbrMap[str(teamName.strip())] = str(abbr)

    return teamAbbrMap

def extractMatchupFromSchedule(matchupSoup, seasonId):
    tds = matchupSoup.find_all('td')
    # first get the date
    matchupDate = tds[0].contents[0]
    startIndex = matchupDate.find('(')
    endIndex = matchupDate.find(')')
    dateRange = matchupDate[startIndex + 1:endIndex]
    # if the start and end of the matchup are in the same month
    # then the date looks like (MON x - y)
    # but if they are in different months
    # then the date looks like (MON x - MON y)
    if re.compile('\w{3}\s\d+ - \w{3}\s\d+').match(dateRange):
        endDateStr = dateRange.split('-')[1].strip()
    else:
        endDateStr = dateRange[:3] + ' ' + dateRange[-2:].strip()
    endDate = datetime.datetime.strptime(seasonId + ' ' + endDateStr, '%Y %b %d').date()

    # then the opponent
    opponent = tds[3].find('a').contents[0].strip()

    return (endDate, opponent)

def teamScheduleToDate(curl, cookieFile, leagueId, seasonId, teamId):
    b = io.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, b.write)
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.COOKIEFILE, cookieFile)
    curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/schedule?leagueId=%s&seasonId=%s&teamId=%s" % (leagueId, seasonId, teamId))
    curl.perform()
    soup = BeautifulSoup(b.getvalue(), "lxml")
    # team name appears as <h1>Team Name Schedule</h1>
    teamName = soup.find_all('h1')[1].contents[0][:-1 * len('Schedule ')].strip()
    schedSoup = soup.find_all('tr')
    matchupRows = [tr for tr in schedSoup[3:] if len(tr.find('td').contents) > 0 and str(tr.find('td').contents[0]).startswith('Matchup')]
    return (teamName, matchupRows)

def getTeamIds(curl, cookieFile, leagueId, seasonId):
    b = io.BytesIO()
    curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/schedule?leagueId=%s&seasonId=%s" % (leagueId, seasonId))
    curl.setopt(pycurl.WRITEFUNCTION, b.write)
    curl.setopt(pycurl.COOKIEFILE, cookieFile)
    curl.perform()
    soup = BeautifulSoup(b.getvalue(), "lxml")
    teamOptions = soup.find('div', class_='bodyCopy').find('select').find_all('option')
    # remove the first option, which is for "All" teams
    return [option.attrs['value'] for option in teamOptions][1:]

def allSchedulesToDate(curl, cookieFile, leagueId, seasonId):
    schedules = {}
    for teamId in getTeamIds(curl, cookieFile, leagueId, seasonId):
        opponents = []
        (teamName, teamMatchupRows) = teamScheduleToDate(curl, cookieFile, leagueId, seasonId, teamId)
        for matchupRow in teamMatchupRows[:3]:
            (endDate, opponent) = extractMatchupFromSchedule(matchupRow, seasonId)
            if datetime.date.today() > endDate:
                opponents.append(opponent)
            else:
                break
        schedules[teamName] = opponents
    return schedules


def getScoreboardSoup(curl, cookieFile, leagueId, seasonId, thisWeek):
    b = io.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, b.write)
    curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/scoreboard?leagueId=%s&seasonId=%s&matchupPeriodId=%s" % (leagueId, seasonId, thisWeek))
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.COOKIEFILE, cookieFile)
    curl.perform()

    soup = BeautifulSoup(b.getvalue(), "lxml")
    return soup.findAll(id='scoreboardMatchups')

def getStandingsSoup(curl, cookieFile, leagueId, seasonId):
    b = io.BytesIO()
    curl.setopt(pycurl.WRITEFUNCTION, b.write)
    curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/standings?leagueId=%s&seasonId=%s" % (leagueId, seasonId))
    curl.setopt(pycurl.FOLLOWLOCATION, 1)
    curl.setopt(pycurl.COOKIEFILE, cookieFile)
    curl.perform()

    soup = BeautifulSoup(b.getvalue(), "lxml")
    return soup.find(id='statsTable')

def cumulativeTotals(standingsSoup, lowerBetterCategories):
    categories = [x.find('a').contents[0] for x in standingsSoup.find_all('tr', class_='tableSubHead')[1].find_all('td', style='width:50px;')]
    statRows = standingsSoup.find_all('tr', class_='tableBody sortableRow')
    totals = {}
    for team in statRows:
        teamName = team.find('td', class_='sortableTeamName').find('a').contents[0].strip()
        totals[teamName] = teamTotals(team.find_all('td', id=re.compile('tmTotalStat*')), categories, lowerBetterCategories)
    return totals

def teamTotals(teamStats, categories, lowerBetterCategories):
    totals = []
    lowerBetterCats = set(lowerBetterCategories.split(','))

    for t in zip(teamStats, categories):
        total = float(t[0].contents[0])
        if t[1] in lowerBetterCats:
            total *= -1
        totals.append(total)

    return totals

def matchupTotals(scoreSoup, lowerBetterCategories):
    pairings = {}
    totals = {}
    for score in scoreSoup:
        matchups = score.findAll('tr', 'tableHead')
        for m in matchups:
            catRow = m.nextSibling
            # the first column is NAME, and the last is SCORE, so ignore them
            categories = [str(x.contents[0]).strip() for x in catRow.findAll('th')[1:-1]]
            
            team1Stats = catRow.nextSibling
            team2Stats = team1Stats.nextSibling
            t1Name = str(team1Stats.find('td', 'teamName').find('a').contents[0]).strip()
            totals[t1Name] = teamTotals(team1Stats.findAll('td', id=re.compile('^total_(\d+)_*')), categories, lowerBetterCategories)

            t2Name = str(team2Stats.find('td', 'teamName').find('a').contents[0]).strip()
            totals[t2Name] = teamTotals(team2Stats.findAll('td', id=re.compile('^total_(\d+)_*')), categories, lowerBetterCategories)

            pairings[t1Name] = t2Name
            pairings[t2Name] = t1Name
    return (totals, pairings)

def calculateRecords(totals):
    records = {}
    for team in totals.keys():
        records[team] = {'wins': 0, 'losses': 0, 'ties': 0}
        for opp in totals.keys():
            if not team == opp:
                wins, losses, ties = 0, 0, 0
                for cat in zip(totals[team], totals[opp]):
                    if cat[0] > cat[1]:
                        wins += 1
                    elif cat[0] < cat[1]:
                        losses += 1
                    else:
                        ties += 1
                records[team][opp] = {'wins': wins, 'losses': losses, 'ties': ties}
                records[team]['wins'] += wins
                records[team]['losses'] += losses
                records[team]['ties'] += ties
    return records

def awp(wins, losses, ties):
    return (wins + ties / 2.0) / (wins + losses + ties)

def determineStandings(records):
    standings = []
    for team in sorted(records.keys()):
        wins = records[team]['wins']
        losses = records[team]['losses']
        ties = records[team]['ties']
        standingRow = {}
        standingRow['awp'] = awp(wins, losses, ties)
        standingRow['team'] = team
        standingRow['record'] = '%s-%s-%s' % (wins, losses, ties)
        standings.append(standingRow)
    return standings

def computeStrengthOfSchedule(standingsSoup, lowerBetterCategories, schedule):
    records = calculateRecords(cumulativeTotals(standingsSoup, lowerBetterCategories))
    oppAwps = {}
    for team in schedule.keys():
        oppWins = oppLosses = oppTies = 0
        for opponent in schedule[team]:
            oppWins += records[opponent]['wins']
            oppLosses += records[opponent]['losses']
            oppTies += records[opponent]['ties']
        oppAwps[team] = awp(oppWins, oppLosses, oppTies)

    return oppAwps
    

def printStandings(leagueName, teamAbbrMap, standings, oppAwps, seasonId, thisWeek):
    print("""
<html>
<head>
  <title>%s %s - Week %s</title>
  <link rel="stylesheet" type="text/css" href="style.css">
</head>
<body>
  <h2>%s %s - Week %s Power Rankings</h2>

  <h3>Power Rankings</h3>
    <table border="1">
      <tr><th>Rank</th><th>Team</th><th><acronym title="Aggregate Winning Percentage">AWP*</acronym></th><th><acronym title="Opponent Aggregate Winning Percentage">OAWP**</acronym></th></tr>
""" % (leagueName, seasonId, thisWeek, leagueName, seasonId, thisWeek))
    rank = 1
    for row in sorted(standings, key=lambda x: x['awp'], reverse=True):
        awp = ("%.3f" % row['awp'])[1:]
        oppAwp = ("%.3f" % oppAwps[row['team']])[1:]
        print("""<tr><td>%d</td><td>%s (%s)</td><td>%s</td><td>%s</td></tr>""" % (rank, row['team'], teamAbbrMap[row['team']], awp, oppAwp))
        rank += 1
    print("""
    </table>

  <br/>""")

def printPowerMatrix(teamAbbrMap, standings, records, matchups=None):
    print("""
  <h3>Relative Power Matrix</h3>
  <i>Actual matchup in <b>bold</b>.
  <br>
  <table border="1">
    <tr>
      <th>TEAM</th>""")

    for team in sorted(teamAbbrMap, key=teamAbbrMap.get):
        print("""      <th><acronym title="%s">%s</acronym></th>""" % (team, teamAbbrMap[team]))

    print("""      <th><acronym title="Aggregate Winning Percentage">AWP*</acronym></th>
    </tr>
""")

    for row in sorted(standings, key=lambda x: teamAbbrMap[x['team']]):
        print("<tr>")
        print('\t<th><acronym title="%s">%s</acronym></th>' % (row['team'], teamAbbrMap[row['team']]))
        wins = records[row['team']]['wins']
        losses = records[row['team']]['losses']
        ties = records[row['team']]['ties']
        for opp in sorted(standings, key=lambda x: teamAbbrMap[x['team']]):
            if row['team'] == opp['team']:
                print("\t<td>&nbsp;</td>")
            else:
                css = ''
                if not matchups == None and matchups[row['team']] == opp['team']:
                    css = 'matchup '
                oppWins = records[row['team']][opp['team']]['wins']
                oppLosses = records[row['team']][opp['team']]['losses']
                oppTies = records[row['team']][opp['team']]['ties']
                if oppWins > oppLosses:
                    css += 'win'
                elif oppWins < oppLosses:
                    css += 'loss'
                else:
                    css += 'tie'
                print("\t<td class=\"%s\">%d-%d-%d</td>" % (css, oppWins, oppLosses, oppTies))
        awp = (wins + ties / 2.0) / (wins + losses + ties)
        awp = ("%.3f" % awp)[1:]
        print("\t<td class=\"total\">%d-%d-%d (%s)</td>" % (wins, losses, ties, awp))
        print("</tr>")

    print("""
</table>
  <br>
  * <i><b>Aggregate Winning Percentage (AWP)</b> - A team's combined record against every other team for the week.</i>
  <br>
  ** <i><b>Opponent Aggregate Winning Percentage (OAWP)</b> - Average AWP of all opponents to date.</i>
  <br /><br />
  <a href="../rankings">Other Weeks</a>
</body>
</html>
""")

def usage():
    print(
"""Usage: %s [-c <file> | --config-file=<file>] [-w <week> | --week=<week> | -s | --season] [-m | --post-message] [-h | --help]
             
    -h, --help                   Print this usage message and quit
    -c <file>, --config=<file>   Configuration file
    -w <week>, --week=<week>     Weekly power rankings for <week>
    -s, --season                 Season power rankings
    -m, --post-message           Post a message""" % sys.argv[0], file=sys.stderr)

def main():
    path = os.path.dirname(sys.argv[0])
    configFile = 'pr.conf'

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:w:smh', ['config=', 'week=', 'season', 'post-message', 'help'])
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
                    print('Error: Argument to -w must be a number', file=sys.stderr)
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
        openingDay = datetime.date(int(properties['startYear']), int(properties['startMonth']), int(properties['startDate']))
        openingWeek = openingDay.isocalendar()[1]
        thisWeek = datetime.date.today().isocalendar()[1] - openingWeek - 1

    curl = pycurl.Curl()
    cookieFile = properties['cookieFile']
    loginESPN(curl, cookieFile, properties['leagueId'], properties['username'], properties['password'])

    teamAbbrMap = getTeamAbbreviations(curl, cookieFile, properties['leagueId'], properties['seasonId'])
    standingsSoup = getStandingsSoup(curl, cookieFile, properties['leagueId'], properties['seasonId'])
    if doWeek:
        scores = getScoreboardSoup(curl, cookieFile, properties['leagueId'], properties['seasonId'], thisWeek)
        (totals, matchups) = matchupTotals(scores, properties['lowerBetter'])
    else:
        totals = cumulativeTotals(standingSoup, properties['lowerBetter'])
        matchups = None
                                    
    records = calculateRecords(totals)
    standings = determineStandings(records)
    schedules = allSchedulesToDate(curl, properties['cookieFile'], properties['leagueId'], properties['seasonId'])
    oppAwps = computeStrengthOfSchedule(standingsSoup, properties['lowerBetter'], schedules)

    printStandings(properties['leagueName'], teamAbbrMap, standings, oppAwps, properties['seasonId'], thisWeek)
    printPowerMatrix(teamAbbrMap, standings, records, matchups)

    if postMessageEnabled == True:
        subject = 'test'
        (ret, fortune) = subprocess.getstatusoutput('fortune fortunes')
        # RANKINGS URL HERE
        msg = "Here are the power rankings for week %s: [link]%s[/link]<br /><br />-- PowerBot" % (thisWeek, properties['rankingsUrl'])
        if ret == 0:
            msg += "<br />[i]%s[/i]" % fortune
        else:
            sys.stderr.write('fortune error')
        postMessage(curl, cookieFile, properties['leagueId'], thisWeek, msg)

if __name__ == '__main__':
    main()
