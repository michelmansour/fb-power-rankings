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

"""
Compute power rankings for an ESPN head-to-head fantasy baseball league.

Classes provided:
PowerRankings -- Perform common operations
WeeklyRankings -- Perform operations specific to weekly rankings
SeasonRankings -- Perform operations specific to season rankings
"""

import requests
from bs4 import BeautifulSoup
import re
import datetime


class PowerRankings:
    """
    Common operations for computing fantasy baseball power rankings.

    This class accepts an ESPN league ID, season ID, and a list of categories
    where a lower score is better and computes power rankings for that league
    in a given time period. Subclasses determine that time period.

    Public methods:
        loginESPN -- Log in to ESPN fantasy sports system
        powerRankings -- Compute power rankings for a time period
        teamAbbreviations -- Retrieve team name abbreviations
        postMessage -- Post a message the league's message board

    Public instance variables:
        None
    """
    _BS_PARSER = "lxml"

    def __init__(self, leagueId, seasonId, lowerBetterCategories):
        """Create a PowerRankings instance.

           Required arguments:
           leagueId -- the ESPN league ID
           seasonID -- the season ID (the year)
           lowerBetterCategories -- a list of scoring category names where a
                                    lower total is better
        """
        self._leagueId = leagueId
        self._seasonId = seasonId
        self._lowerBetterCategories = lowerBetterCategories
        self._session = requests.Session()

    def loginESPN(self, username, password):
        """Log in to the ESPN fantasy sports system.

           This method must be called first for private leagues.

           Required arguments:
           username -- the login username
           password -- the login password
        """
        postData = {
            'SUBMIT': '1',
            'aff_code': 'espn_fantgames',
            'appRedirect':
                'http://games.espn.go.com/flb/leagueoffice?\
                leagueId=%s&seasonId=%s' %
                (self._leagueId, self._seasonId),
            'cookieDomain': '.go.com',
            'failedLocation':
                'http://games.espn.go.com/flb/signin?\
                redir=http%%3A%%2F%%2Fgames.espn.go.com%%2Fflb%%2Fleagueoffice\
                %%3FleagueId%%3D%s%%26seasonId%%3D%s&e=1' %
                (self._leagueId, self._seasonId),
            'multipleDomains': 'true',
            'password': password,
            'submit': 'Sign In',
            'username': username,
            'failedAttempts': '2'
        }
        self._session.post("https://r.espn.go.com/espn/fantasy/login",
                           params=postData)

    def postMessage(self, message, subject='Power Rankings'):
        """Post a message to the league message board.

           Required arguments:
           message -- the message to post

           Keyword arguments:
           subject -- the message subject (default 'Power Rankings')
        """
        params = {
            'leagueId': self._leagueId,
            'seasonId': self._seasonId,
            'subject': subject,
            'body': message,
            'btnSubmit': 'Submit Message',
            'typeId': '0',
            'topicId': '0',
            'redir': '/flb/leagueoffice?leagueId=%s' % self._leagueId,
            'incoming': '1'
        }
        self._session.post('http://games.espn.go.com/flb/tools/postmessage',
                           params=params)

    def teamAbbreviations(self):
        """Get a dictionary of team names to their abbreviated versions.

           The keys of this dictionary (ie, the team names) are the same as the
           values of the 'team' key in the dictionary produced by the
           powerRankings method.
        """
        teamAbbrMap = {}

        r = self._session.get(
            'http://games.espn.go.com/flb/leaguesetup/ownerinfo',
            params={'leagueId': self._leagueId,
                    'seasonId': self._seasonId})
        soup = BeautifulSoup(r.text, PowerRankings._BS_PARSER)
        ownerRows = soup.findAll("tr", "ownerRow")
        for row in ownerRows:
            cells = row.findAll("td")
            if re.compile("[0-9]+").match(str(cells[0].contents[0])):
                abbr = cells[1].contents[0]
                teamName = cells[2].findAll('a')[0].contents[0]
                teamAbbrMap[str(teamName.strip())] = str(abbr)

        return teamAbbrMap

    def _extractMatchup(self, matchupSoup):
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
        endDate = datetime.datetime.strptime(self._seasonId + ' ' + endDateStr,
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

    def _teamSchedule(self, teamId):
        r = self._session.get('http://games.espn.go.com/flb/schedule',
                              params={'leagueId': self._leagueId,
                                      'seasonId': self._seasonId,
                                      'teamId': teamId})
        soup = BeautifulSoup(r.text, PowerRankings._BS_PARSER)
        # team name appears as <h1>Team Name Schedule</h1>
        teamName = soup.find_all('h1')[1].contents[0][:-1 *
                                                      len('Schedule ')].strip()
        schedSoup = soup.find_all('tr')
        matchupRows = [tr for tr in schedSoup[3:]
                       if len(tr.find('td').contents) > 0 and
                       str(tr.find('td').contents[0]).startswith('Matchup')]
        return (teamName, matchupRows)

    def _teamIds(self):
        r = self._session.get('http://games.espn.go.com/flb/schedule',
                              params={'leagueId': self._leagueId,
                                      'seasonId': self._seasonId})
        soup = BeautifulSoup(r.text, PowerRankings._BS_PARSER)
        teamOptions = soup.find('div', class_='bodyCopy').\
            find('select').find_all('option')
        # remove the first option, which is for "All" teams
        return [option.attrs['value'] for option in teamOptions][1:]

    def _allSchedules(self):
        schedules = {}
        for teamId in self._teamIds():
            opponents = []
            (teamName, teamMatchupRows) = self._teamSchedule(teamId)
            for matchupRow in teamMatchupRows[:3]:
                (endDate, opponent) = self._extractMatchup(matchupRow)
                if endDate is not None and datetime.date.today() > endDate:
                    opponents.append(opponent)
                else:
                    break
            schedules[teamName] = opponents
        return schedules

    def _teamTotals(self, teamStats, categories):
        totals = []

        for t in zip(teamStats, categories):
            total = float(t[0].contents[0])
            if t[1] in self._lowerBetterCategories:
                total *= -1
            totals.append(total)

        return totals

    def _totals():
        pass

    def _powerMatrix(self):
        records = {}
        (totals, pairings) = self._totals()
        for team in totals.keys():
            records[team] = {'wins': 0, 'losses': 0, 'ties': 0,
                             'opp': None, 'oppRecords': {}}
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

    def _standingsSoup(self):
        r = self._session.get('http://games.espn.go.com/flb/standings',
                              params={'leagueId': self._leagueId,
                                      'seasonId': self._seasonId})
        soup = BeautifulSoup(r.text, PowerRankings._BS_PARSER)
        return soup.find(id='statsTable')

    def _cumulativeTotals(self):
        standingsSoup = self._standingsSoup()
        categories = [x.find('a').contents[0] for x in
                      standingsSoup.find_all('tr', class_='tableSubHead')[1].
                      find_all('td', style='width:50px;')]
        statRows = standingsSoup.find_all('tr', class_='tableBody sortableRow')
        totals = {}
        for team in statRows:
            teamName = team.find('td', class_='sortableTeamName').find('a').\
                contents[0].strip()
            totals[teamName] = self._teamTotals(team.
                                                find_all('td',
                                                         id=re.compile(
                                                             'tmTotalStat*')),
                                                categories)
        return (totals, {})

    def _strengthOfSchedule(self):
        records = self._powerMatrix()
        schedule = self._allSchedules()
        oppAwps = {}
        for team in schedule.keys():
            oppWins = oppLosses = oppTies = 0
            for opponent in schedule[team]:
                oppWins += records[opponent]['wins']
                oppLosses += records[opponent]['losses']
                oppTies += records[opponent]['ties']
            oppAwps[team] = PowerRankings._awp(oppWins, oppLosses, oppTies)

        return oppAwps

    @staticmethod
    def _awp(wins, losses, ties):
        return (wins + ties / 2.0) / (wins + losses + ties)

    def powerRankings(self):
        """Compute and return the power rankings.

           The power rankings structure is a list of nested dicts. Each dict in
           the list has the following key-value pairs:
               'team' -- the team name (a string)
               'wins' -- the number of wins (an integer)
               'losses' -- the number of losses (an integer)
               'ties' -- the number of ties (an integer)
               'awp' -- the aggregate winning percentage (a float)
               'oppAwp' -- the cumulative AWP of the team's opponents to date
               'matchupOpp' -- the team's opponent during the matchup period
                               or None, if there is no matchup period
               'powerRow' -- a dict of the team's record against every other
                             team in the league for the time period applying
                             to the power rankings (week or season). The keys
                             are the names of the other teams in the league,
                             and the values are dictionaries with keys:
                                 'wins' -- wins against this opponent
                                 'losses' -- losses against this opponent
                                 'ties' -- ties against this opponent.

               To get a team's record against every other team in the league:

               for opp in pr.powerRankings()['My Team']['powerRow']:
                   print("Record against %s: %d-%d-%d" %
                          opp, opp['wins'], opp['losses'], opp['ties'])
        """
        oppAwps = self._strengthOfSchedule()
        powerMatrix = self._powerMatrix()
        standings = []
        for team in sorted(powerMatrix.keys()):
            wins = powerMatrix[team]['wins']
            losses = powerMatrix[team]['losses']
            ties = powerMatrix[team]['ties']
            standingRow = {'team': team, 'wins': wins, 'losses': losses,
                           'ties': ties}
            standingRow['awp'] = PowerRankings._awp(wins, losses, ties)
            standingRow['oppAwp'] = oppAwps[team]
            standingRow['matchupOpp'] = powerMatrix[team]['opp']
            standingRow['powerRow'] = powerMatrix[team]['oppRecords']
            standings.append(standingRow)

        rank = 1
        for row in sorted(standings, key=lambda x: x['awp'], reverse=True):
            row['rank'] = rank
            rank += 1

        return sorted(standings, key=lambda x: x['rank'])


class WeeklyRankings(PowerRankings):
    """Compute weekly power rankings."""

    def __init__(self, leagueId, seasonId, lowerBetterCategories, week):
        """Create a WeeklyRankings instance.

           Override PowerRankings.__init__
           Required Arguments:
           leagueId -- the ESPN league ID
           seasonId -- the season ID (the year)
           lowerBetterCategories -- a list of scoring category names where a
                                    lower score is better
           week -- the week (matchup period) to compute the rankings for
        """
        PowerRankings.__init__(self, leagueId, seasonId, lowerBetterCategories)
        self._week = week

    def _scoreboardSoup(self):
        r = self._session.get('http://games.espn.go.com/flb/scoreboard',
                              params={'leagueId': self._leagueId,
                                      'seasonId': self._seasonId,
                                      'matchupPeriodId': self._week})
        soup = BeautifulSoup(r.text, PowerRankings._BS_PARSER)
        return soup.findAll(id='scoreboardMatchups')

    def _parseStats(self, statsSoup, categories):
        return self._teamTotals(
            statsSoup.findAll('td', id=re.compile('^total_(\d+)_*')),
            categories)

    def _parseTeamName(self, statsSoup):
        return str(statsSoup.find('td', 'teamName').find('a').contents[0]).strip()

    def _totals(self):
        pairings = {}
        totals = {}
        scoreSoup = self._scoreboardSoup()
        for score in scoreSoup:
            matchups = score.findAll('tr', 'tableHead')
            for m in matchups:
                catRow = m.nextSibling
                # first column is NAME and last is SCORE, so ignore them
                categories = [str(x.contents[0]).strip()
                              for x in catRow.findAll('th')[1:-1]]

                team1Stats = catRow.nextSibling
                team2Stats = team1Stats.nextSibling
                t1Name = self._parseTeamName(team1Stats)
                t2Name = self._parseTeamName(team2Stats)
                totals[t1Name] = self._parseStats(team1Stats, categories)
                totals[t2Name] = self._parseStats(team2Stats, categories)

                pairings[t1Name] = t2Name
                pairings[t2Name] = t1Name
        return (totals, pairings)


class SeasonRankings(PowerRankings):
    """Compute cumulative season power rankings to date."""
    def _totals(self):
        return self._cumulativeTotals()
