# Fantasy Baseball Power Rankings

## Overview
This is a small Python 3 script to compute power rankings in ESPN head-to-head
fantasy baseball leagues. There are often unfair results in H2H, so these power
rankings are an attempt to make owners who got robbed feel a little better about
their teams.

### Methodology
It does this by computing, for each team, an _aggregate winning percentage_ (AWP)(tm).
AWP is simply a team's record against every other team during a given time period,
either a week or an entire season. This way managers can see that the only reason
their team did so badly this week was because they were playing the best team
in the league, while the team below them vaulted over them into playoff position
by virtue of playing the league doormat. You'll get them next week.

### Output
The script produces an HTML page containing team standings according to the AWP
records, and a Relative Power Matrix(tm), showing how every team would have fared against
every other team. The standings also list each team's cumulative opponent AWP to date.
Sometimes I manually edit the standings to add a witty comment
about how each team performed, much like professional power rankings do (but
funnier). The output is further controlled by a stylesheet, which you are free
and encouraged to modify.

## Usage

### Configuration
To generate the power rankings, the script needs several pieces of information
from a configuration file. The configuration parameters are:
* __leagueId__ - Your ESPN League ID number, usually found in the URL of any of your league's pages
* __seasonId__ - Another URL paramemter, for the season; it's just the year
* __username__ - The user you will log in to ESPN with
* __password__ - The above user's password
* __cookieFile__ - A file to store the ESPN login cookie in
* __leagueName__ - Name of the league to show in the output
* __startYear__ - For cumulative power rankings, the year to start in
* __startMonth__ - Start month for cumulative rankings
* __startDate__ - Start day of month for cumulative rankings
* __lowerBetter__ - Categories where a lower score is better. Separate abbreviations by commas.
* __rankingsUrl__ - Where the rankings are hosted. Included in post to league message board.

The script will use the supplied credentials to log in to your league,
identified by the league ID and season ID, using cURL (see below). The login
cookie will be saved in the specified cookie file.

__startYear__, __startMonth__, and __startDate__ should correspond to the first
day of competition for the season to get cumulative power rankings.

### Running the Script
    $ python rankings_cli.py -h
    Usage: rankings_cli.py [-c <file> | --config-file=<file>] [-w <week> | --week=<week> | -s | --season] [-m | --post-message] [-h | --help]

         -h, --help                   Print this usage message and quit
         -c <file>, --config=<file>   Configuration file
         -w <week>, --week=<week>     Weekly power rankings for <week>
         -s, --season                 Season power rankings
         -m, --post-message           Post a message

If `-c` or `--config` is provided, then `<file>` is the configuration file to use. By default,
the script looks for the configuration options in a file called `pr.conf`

If `-w` or `--week` is provided, then the rankings for `<week>` are calculated.
Otherwise, rankings for the most recent week are calculated.

If `-s` or `--season` is provided, then cumulative rankings for the entire season
to date are calculated.

If `-m` or `--post-message` is specified, then a message will be posted to your league's message board by
your user on behalf of PowerBot(tm), a sassy robot who wouldn't mind seeing the
extinction of humans. It will pull quotes from the `fortune` command if available, and
it will tell your league mates where to find the rankings, via the __rankingsUrl__
configuration property. Feel free to modify it as needed. Also, it doesn't like being
referred to as "it".

### Dependencies
This part is so very important, and yet so far down the page. This program has a few
critical dependencies, which are specified in the `requirements.txt` file.
Dependencies can be installed using *pip*: `pip install -r requirements.txt`

Most critically, it only works with **Python 3**. However, the Python 2
version can still be found in the `python2` branch.

Second most critically, it depends on [PycURL][1]. Which means it's probably
easiest to run this thing on a *NIX system.

[1]: http://pycurl.sourceforge.net/

Last most critically, it depends on the venerable [Beautiful Soup][2] library.
Additionally, it uses [lxml][3] as Beautiful Soup's underlying HTML parser.
The Beautiful Soup documentation contains information on [installing lxml][4].
The Python 3 code only works with Beautiful Soup 4, while the Python 2
branch has only been tested to work with Beautiful Soup 3.

[2]: http://www.crummy.com/software/BeautifulSoup/
[3]: http://lxml.de/
[4]: http://www.crummy.com/software/BeautifulSoup/bs4/doc/#installing-a-parser



## License and Copyright
Distributed under the MIT License.
Copyright (c) 2014 Michel Mansour.
