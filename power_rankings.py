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

import requests
from bs4 import BeautifulSoup
import re
import datetime


class PowerRankings:
    BS_PARSER = "lxml"

    def __init__(self, leagueId, seasonId, lowerBetterCategories):
        self.leagueId = leagueId
        self.seasonId = seasonId
        self.lowerBetterCategories = lowerBetterCategories
        self.session = requests.Session()

    def loginESPN(self, username, password):
        postData = {
            'SUBMIT': '1',
            'aff_code': 'espn_fantgames',
            'appRedirect':
                'http://games.espn.go.com/flb/leagueoffice?\
                leagueId=%s&seasonId=%s' %
                (self.leagueId, self.seasonId),
            'cookieDomain': '.go.com',
            'failedLocation':
                'http://games.espn.go.com/flb/signin?\
                redir=http%%3A%%2F%%2Fgames.espn.go.com%%2Fflb%%2Fleagueoffice\
                %%3FleagueId%%3D%s%%26seasonId%%3D%s&e=1' %
                (self.leagueId, self.seasonId),
            'multipleDomains': 'true',
            'password': password,
            'submit': 'Sign In',
            'username': username,
            'failedAttempts': '2'
        }
        self.session.post("https://r.espn.go.com/espn/fantasy/login",
                          params=postData)

    def postMessage(self, thisWeek, message, subject=''):
        if subject == '':
            subject = 'Power Rankings: Week %s' % thisWeek

        params = {
            'leagueId': self.leagueId,
            'seasonId': self.seasonId,
            'subject': subject,
            'body': message,
            'btnSubmit': 'Submit Message',
            'typeId': '0',
            'topicId': '0',
            'redir': '/flb/leagueoffice?leagueId=%s' % self.leagueId,
            'incoming': '1'
        }
        self.session.post('http://games.espn.go.com/flb/tools/postmessage',
                          params=params)

    def teamAbbreviations(self):
        teamAbbrMap = {}

        r = self.session.get(
            'http://games.espn.go.com/flb/leaguesetup/ownerinfo',
            params={'leagueId': self.leagueId,
                    'seasonId': self.seasonId})
        soup = BeautifulSoup(r.text, PowerRankings.BS_PARSER)
        ownerRows = soup.findAll("tr", "ownerRow")
        for row in ownerRows:
            cells = row.findAll("td")
            if re.compile("[0-9]+").match(str(cells[0].contents[0])):
                abbr = cells[1].contents[0]
                teamName = cells[2].findAll('a')[0].contents[0]
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
        endDate = datetime.datetime.strptime(self.seasonId + ' ' + endDateStr,
                                             '%Y %b %d').date()

        # then the opponent
        # there is no way to tell that we've looked at the whole season except
        # that the number of columns has changed
        # also, in some years, a column is added indicating the team's record
        # to that point, but the opponent is always the second-to-last column
        if len(tds) >= 4:
            opponent = tds[-2].find('a').contents[0].strip()
        else:
            endDate = None

        return (endDate, opponent)

    def teamScheduleToDate(self, teamId):
        r = self.session.get('http://games.espn.go.com/flb/schedule',
                             params={'leagueId': self.leagueId,
                                     'seasonId': self.seasonId,
                                     'teamId': teamId})
        soup = BeautifulSoup(r.text, PowerRankings.BS_PARSER)
        # team name appears as <h1>Team Name Schedule</h1>
        teamName = soup.find_all('h1')[1].contents[0][:-1 *
                                                      len('Schedule ')].strip()
        schedSoup = soup.find_all('tr')
        matchupRows = [tr for tr in schedSoup[3:]
                       if len(tr.find('td').contents) > 0 and
                       str(tr.find('td').contents[0]).startswith('Matchup')]
        return (teamName, matchupRows)

    def teamIds(self):
        r = self.session.get('http://games.espn.go.com/flb/schedule',
                             params={'leagueId': self.leagueId,
                                     'seasonId': self.seasonId})
        soup = BeautifulSoup(r.text, PowerRankings.BS_PARSER)
        teamOptions = soup.find('div', class_='bodyCopy').\
            find('select').find_all('option')
        # remove the first option, which is for "All" teams
        return [option.attrs['value'] for option in teamOptions][1:]

    def allSchedulesToDate(self):
        schedules = {}
        for teamId in self.teamIds():
            opponents = []
            (teamName, teamMatchupRows) = self.teamScheduleToDate(teamId)
            for matchupRow in teamMatchupRows[:3]:
                (endDate, opponent) = self.extractMatchupFromSchedule(matchupRow)
                if endDate is not None and datetime.date.today() > endDate:
                    opponents.append(opponent)
                else:
                    break
            schedules[teamName] = opponents
        return schedules

    def teamTotals(self, teamStats, categories):
        totals = []

        for t in zip(teamStats, categories):
            total = float(t[0].contents[0])
            if t[1] in self.lowerBetterCategories:
                total *= -1
            totals.append(total)

        return totals

    def totals():
        return

    def powerMatrix(self):
        records = {}
        (totals, pairings) = self.totals()
        for team in totals.keys():
            records[team] = {'wins': 0, 'losses': 0, 'ties': 0,
                             'oppRecords': {}}
            if team in pairings:
                records[team]['opp'] = pairings[team]
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
                    records[team]['oppRecords'][opp] = {'wins': wins,
                                                        'losses': losses,
                                                        'ties': ties}
                    records[team]['wins'] += wins
                    records[team]['losses'] += losses
                    records[team]['ties'] += ties
        return records

    def standingsSoup(self):
        r = self.session.get('http://games.espn.go.com/flb/standings',
                             params={'leagueId': self.leagueId,
                                     'seasonId': self.seasonId})
        soup = BeautifulSoup(r.text, PowerRankings.BS_PARSER)
        return soup.find(id='statsTable')

    def cumulativeTotals(self):
        standingsSoup = self.standingsSoup()
        categories = [x.find('a').contents[0] for x in
                      standingsSoup.find_all('tr', class_='tableSubHead')[1].
                      find_all('td', style='width:50px;')]
        statRows = standingsSoup.find_all('tr', class_='tableBody sortableRow')
        totals = {}
        for team in statRows:
            teamName = team.find('td', class_='sortableTeamName').find('a').\
                contents[0].strip()
            totals[teamName] = self.teamTotals(team.
                                               find_all('td',
                                                        id=re.compile(
                                                            'tmTotalStat*')),
                                               categories)
        return (totals, {})

    def computeStrengthOfSchedule(self):
        records = self.powerMatrix()
        schedule = self.allSchedulesToDate()
        oppAwps = {}
        for team in schedule.keys():
            oppWins = oppLosses = oppTies = 0
            for opponent in schedule[team]:
                oppWins += records[opponent]['wins']
                oppLosses += records[opponent]['losses']
                oppTies += records[opponent]['ties']
            oppAwps[team] = PowerRankings.awp(oppWins, oppLosses, oppTies)

        return oppAwps

    @staticmethod
    def awp(wins, losses, ties):
        return (wins + ties / 2.0) / (wins + losses + ties)

    def standings(self):
        oppAwps = self.computeStrengthOfSchedule()
        powerMatrix = self.powerMatrix()
        standings = []
        for team in sorted(powerMatrix.keys()):
            wins = powerMatrix[team]['wins']
            losses = powerMatrix[team]['losses']
            ties = powerMatrix[team]['ties']
            standingRow = {'wins': wins, 'losses': losses, 'ties': ties}
            standingRow['awp'] = PowerRankings.awp(wins, losses, ties)
            standingRow['oppAwp'] = oppAwps[team]
            standingRow['team'] = team
            standingRow['record'] = '%s-%s-%s' % (wins, losses, ties)
            standingRow['powerRow'] = powerMatrix[team]
            standings.append(standingRow)

        rank = 1
        for row in sorted(standings, key=lambda x: x['awp'], reverse=True):
            row['rank'] = rank
            rank += 1

        return sorted(standings, key=lambda x: x['rank'])


class WeeklyRankings(PowerRankings):
    def __init__(self, leagueId, seasonId, lowerBetterCategories, week):
        PowerRankings.__init__(self, leagueId, seasonId, lowerBetterCategories)
        self.week = week

    def scoreboardSoup(self):
        r = self.session.get('http://games.espn.go.com/flb/scoreboard',
                             params={'leagueId': self.leagueId,
                                     'seasonId': self.seasonId,
                                     'matchupPeriodId': self.week})
        soup = BeautifulSoup(r.text, PowerRankings.BS_PARSER)
        return soup.findAll(id='scoreboardMatchups')

    def parseStats(self, statsSoup, categories):
        return self.teamTotals(
            statsSoup.findAll('td', id=re.compile('^total_(\d+)_*')),
            categories)

    def parseTeamName(self, statsSoup):
        return str(statsSoup.find('td', 'teamName').find('a').contents[0]).strip()

    def totals(self):
        pairings = {}
        totals = {}
        scoreSoup = self.scoreboardSoup()
        for score in scoreSoup:
            matchups = score.findAll('tr', 'tableHead')
            for m in matchups:
                catRow = m.nextSibling
                # first column is NAME and last is SCORE, so ignore them
                categories = [str(x.contents[0]).strip()
                              for x in catRow.findAll('th')[1:-1]]

                team1Stats = catRow.nextSibling
                team2Stats = team1Stats.nextSibling
                t1Name = self.parseTeamName(team1Stats)
                t2Name = self.parseTeamName(team2Stats)
                totals[t1Name] = self.parseStats(team1Stats, categories)
                totals[t2Name] = self.parseStats(team2Stats, categories)

                pairings[t1Name] = t2Name
                pairings[t2Name] = t1Name
        return (totals, pairings)


class SeasonRankings(PowerRankings):
    def totals(self):
        return self.cumulativeTotals()
