Use UniversalLogParser.py to parse a log file and get a concise output, along with the relevant connection state and signal quality data as plots in a webpage.

usage: UniversalLogParser.py [-h] [-o O] [-k] [-d] [-e] [--regex] [--fromto (from) - (to)][filename]

positional arguments:

  filename              name of log file to parse

optional arguments:

  -h, --help            show this help message and exit

  -o O                  Output format. plot, dict, csv, or json(default plot).
                        Onlyplot creates a webpage plot. The other options
                        generate a data file in the specified format. json
                        outputs are plottable from the"choose a different file
                        to plot" button on the page

  -k                    Keep the common format log file. This is useful since
                        line numbers in the concise output refrence the common
                        log format

  -d                    Use if there are debug lines in the log file. Will
                        plot more charts

  -e                    Will write error messages to concise log file

  --regex               Use to enter a menu where additional regular expressions can be supplied

  --fromto		Specify a date and time range in the form (from) - (to) where (from) or (to) 
			are of the form (year)-(month)-(day) (24-hour):(minute):(second)
			Leave one or both blank to have the range open ended: 
			MUST STILL HAVE THE DASH. 
			ex: --fromto 2019-04-24 13:03:43 - 2019-04-25 02:22:15
			ex: --fromto - 2020-07-17 13:21:44

The files are created by default in the root directory, wherever UniversalLogParser is. File paths for log files can be specified.
The names of the files created are data_{filename}, concise_{filename}, and {filename}.html. The data file is only there if you want to manually load it from the webpage.

LINUX:

Must use 'python3' since earlier can't handle some characters present

General Usage: 

python3 [path to UniversalLogParser.py] [path to log file]

If you don't have python, run 'sudo apt-get install python3'

WINDOWS:

If you don't have python installed, install the latest (3.8.3) from the python site, or even the windows 10 app store. (I did test, this actually works)

General usage: 

In command prompt window type the following

python [path to UniversalLogParser.py] [path to log file]


TIPS:

It makes it easier if the command prompt/terminal window is in the directory where UniversalLogParser.py is. Even more so if the log files are in the same location.

