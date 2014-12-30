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

class PowerRankings:
    def __init__(self, cookieFile, leagueId, seasonId, lowerBetterCategories):
        self.cookieFile = cookieFile
        self.leagueId = leagueId
        self.seasonId = seasonId
        self.lowerBetterCategories = lowerBetterCategories
        self.curl = pycurl.Curl()
        
    def loginESPN(self, username, password):
        fp = open('/dev/null', 'wb')

        self.curl.setopt(pycurl.WRITEDATA, fp)
        self.curl.setopt(pycurl.URL, "https://r.espn.go.com/espn/fantasy/login")
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.COOKIEFILE, self.cookieFile)
        self.curl.setopt(pycurl.POST, 1)
        self.curl.setopt(pycurl.POSTFIELDS, "failedAttempts=2&SUBMIT=1&failedLocation=http://games.espn.go.com/flb/signin?redir=http%%3A%%2F%%2Fgames.espn.go.com%%2Fflb%%2Fstandings%%3FleagueId%%3D%s%%26e=1%%26aff_code=espn_fantgames&appRedirect=http://games.espn.go.com/flb/standings?leagueId=%s&cookieDomain=.go.com&multipleDomains=true&username=%s&password=%s&submit=Sign+In" % (self.leagueId, self.leagueId, username, password))
        self.curl.perform()

    def postMessage(self, thisWeek, message, subject=''):
        if subject == '':
            subject = 'Power Rankings: Week %s' % thisWeek

        self.curl.setopt(pycurl.URL, 'http://games.espn.go.com/flb/tools/postmessage?leagueId=%s&typeId=0&topicId=0' % self.leagueId)
        self.curl.setopt(pycurl.COOKIEFILE, self.cookieFile)
        self.curl.setopt(pycurl.POST, 1)
        self.curl.setopt(pycurl.POSTFIELDS, 'subject=%s&body=%s&btnSubmit=Submit+Message&typeId=0&topicId=0&redir=/flb/leagueoffice?leagueId=%s&incoming=1' % (subject, message, self.leagueId))
        self.curl.perform()

    def getTeamAbbreviations(self):
        teamAbbrMap = {}

        b = io.BytesIO()
        self.curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/leaguesetup/ownerinfo?leagueId=%s&seasonId=%s" % (self.leagueId, self.seasonId))
        self.curl.setopt(pycurl.WRITEFUNCTION, b.write)
        self.curl.setopt(pycurl.COOKIEFILE, self.cookieFile)
        self.curl.perform()
        soup = BeautifulSoup(b.getvalue(), "lxml")
        b.close()
        ownerRows = soup.findAll("tr", "ownerRow")
        for row in ownerRows:
            cells = row.findAll("td")
            if re.compile("[0-9]+").match(str(cells[0].contents[0])):
                abbr = cells[1].contents[0]
                teamName = cells[2].findAll('a')[0].contents[0];
                teamAbbrMap[str(teamName.strip())] = str(abbr)

        return teamAbbrMap

    def extractMatchupFromSchedule(self, matchupSoup):
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
        endDate = datetime.datetime.strptime(self.seasonId + ' ' + endDateStr, '%Y %b %d').date()

        # then the opponent
        opponent = tds[3].find('a').contents[0].strip()

        return (endDate, opponent)

    def teamScheduleToDate(self, teamId):
        b = io.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, b.write)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.COOKIEFILE, self.cookieFile)
        self.curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/schedule?leagueId=%s&seasonId=%s&teamId=%s" % (self.leagueId, self.seasonId, teamId))
        self.curl.perform()
        
        soup = BeautifulSoup(b.getvalue(), "lxml")
        # team name appears as <h1>Team Name Schedule</h1>
        teamName = soup.find_all('h1')[1].contents[0][:-1 * len('Schedule ')].strip()
        schedSoup = soup.find_all('tr')
        matchupRows = [tr for tr in schedSoup[3:] if len(tr.find('td').contents) > 0 and str(tr.find('td').contents[0]).startswith('Matchup')]
        return (teamName, matchupRows)

    def getTeamIds(self):
        b = io.BytesIO()
        self.curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/schedule?leagueId=%s&seasonId=%s" % (self.leagueId, self.seasonId))
        self.curl.setopt(pycurl.WRITEFUNCTION, b.write)
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.COOKIEFILE, self.cookieFile)
        self.curl.perform()

        soup = BeautifulSoup(b.getvalue(), "lxml")
        teamOptions = soup.find('div', class_='bodyCopy').find('select').find_all('option')
        # remove the first option, which is for "All" teams
        return [option.attrs['value'] for option in teamOptions][1:]

    def allSchedulesToDate(self):
        schedules = {}
        for teamId in self.getTeamIds():
            opponents = []
            (teamName, teamMatchupRows) = self.teamScheduleToDate(teamId)
            for matchupRow in teamMatchupRows[:3]:
                (endDate, opponent) = self.extractMatchupFromSchedule(matchupRow)
                if datetime.date.today() > endDate:
                    opponents.append(opponent)
                else:
                    break
            schedules[teamName] = opponents
        return schedules


    def getScoreboardSoup(self, thisWeek):
        b = io.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, b.write)
        self.curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/scoreboard?leagueId=%s&seasonId=%s&matchupPeriodId=%s" % (self.leagueId, self.seasonId, thisWeek))
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.COOKIEFILE, self.cookieFile)
        self.curl.perform()

        soup = BeautifulSoup(b.getvalue(), "lxml")
        return soup.findAll(id='scoreboardMatchups')

    def getStandingsSoup(self):
        b = io.BytesIO()
        self.curl.setopt(pycurl.WRITEFUNCTION, b.write)
        self.curl.setopt(pycurl.URL, "http://games.espn.go.com/flb/standings?leagueId=%s&seasonId=%s" % (self.leagueId, self.seasonId))
        self.curl.setopt(pycurl.FOLLOWLOCATION, 1)
        self.curl.setopt(pycurl.COOKIEFILE, self.cookieFile)
        self.curl.perform()

        soup = BeautifulSoup(b.getvalue(), "lxml")
        return soup.find(id='statsTable')

    def cumulativeTotals(self, standingsSoup):
        categories = [x.find('a').contents[0] for x in standingsSoup.find_all('tr', class_='tableSubHead')[1].find_all('td', style='width:50px;')]
        statRows = standingsSoup.find_all('tr', class_='tableBody sortableRow')
        totals = {}
        for team in statRows:
            teamName = team.find('td', class_='sortableTeamName').find('a').contents[0].strip()
            totals[teamName] = self.teamTotals(team.find_all('td', id=re.compile('tmTotalStat*')), categories)
        return totals

    def teamTotals(self, teamStats, categories):
        totals = []
        lowerBetterCats = set(self.lowerBetterCategories.split(','))

        for t in zip(teamStats, categories):
            total = float(t[0].contents[0])
            if t[1] in lowerBetterCats:
                total *= -1
            totals.append(total)

        return totals

    def matchupTotals(self, scoreSoup):
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
                totals[t1Name] = self.teamTotals(team1Stats.findAll('td', id=re.compile('^total_(\d+)_*')), categories)

                t2Name = str(team2Stats.find('td', 'teamName').find('a').contents[0]).strip()
                totals[t2Name] = self.teamTotals(team2Stats.findAll('td', id=re.compile('^total_(\d+)_*')), categories)

                pairings[t1Name] = t2Name
                pairings[t2Name] = t1Name
        return (totals, pairings)

    def calculateRecords(self, totals):
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

    @staticmethod
    def awp(wins, losses, ties):
        return (wins + ties / 2.0) / (wins + losses + ties)

    def determineStandings(self, records):
        standings = []
        for team in sorted(records.keys()):
            wins = records[team]['wins']
            losses = records[team]['losses']
            ties = records[team]['ties']
            standingRow = {}
            standingRow['awp'] = PowerRankings.awp(wins, losses, ties)
            standingRow['team'] = team
            standingRow['record'] = '%s-%s-%s' % (wins, losses, ties)
            standings.append(standingRow)

        rank = 1
        for row in sorted(standings, key=lambda x: x['awp'], reverse=True):
            row['rank'] = rank
            rank += 1
        
        return sorted(standings, key=lambda x: x['rank'])

    def computeStrengthOfSchedule(self, standingsSoup, schedule):
        records = self.calculateRecords(self.cumulativeTotals(standingsSoup))
        oppAwps = {}
        for team in schedule.keys():
            oppWins = oppLosses = oppTies = 0
            for opponent in schedule[team]:
                oppWins += records[opponent]['wins']
                oppLosses += records[opponent]['losses']
                oppTies += records[opponent]['ties']
            oppAwps[team] = PowerRankings.awp(oppWins, oppLosses, oppTies)

        return oppAwps
