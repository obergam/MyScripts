import argparse
import re
from datetime import datetime, timedelta
import json
import tempfile
import calendar
import webbrowser
from copy import copy


def utc_to_local(utc_dt):
    """Helper method for some logs since they use UTC time. Converts UTC to local timezone"""
    timestamp = calendar.timegm(utc_dt.timetuple())
    local_dt = datetime.fromtimestamp(timestamp)
    assert utc_dt.resolution >= timedelta(microseconds=1)
    return local_dt.replace(microsecond=utc_dt.microsecond)


def format_dt(dt):
    return dt.strftime(LogTranslator.OUTPUT_DATE_FORMAT)


# Base Class for all translators
class LogTranslator(object):
    """Base class for custom translator classes.  Translators will read a log file in one format (like
	   NCM export, router UI export, syslog, CLI log command, etc), and emit a "common" log file used
	   by the various log file parsers for user-friendly consumption."""
    OUTPUT_FORMAT = '{} {} S= {} {} -- {}\n'
    # Out Format:   DATE IP    lvl      src      msg
    OUTPUT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        super().__init__()

        # Interface flags
        self._abortParse = False  # Stop parsing the file (we're done with log content)

    @classmethod
    def detect(cls, logFile):
        """Detect the source file type for this translator.  Return True if the source logFile appears
		   to be a log file of this type, False otherwise.  Note that you should reset the file pointer
		   if you are going to return False, as another "detector" function will be invoked using the
		   same file pointer.  If you return True, it is acceptable to leave the pointer wherever you please,
		   as the next method to be invoked will be the file translate method."""
        pass

    @property
    def abort(self):
        """Interface method to inform caller that parsing is finished before the file-end.  Useful for
		   aggregated logs that only need to look at a portion of the log file."""
        return self._abortParse

    def writeOutputLine(self, timestamp, ip, logLevel, msgSource, logMessage):
        """Helper method for writing output messages.  Called by translateLine"""
        return self.OUTPUT_FORMAT.format(timestamp, ip, logLevel, msgSource, logMessage)

    def translateLine(self, ln):
        """Translate an individual line of a log file into the common log output format.  If the line does
		   not match, return None to avoid writing anything to the output file.  Should be overridden."""
        return ln


# From socket listening
class SyslogTranslator(LogTranslator):
    @classmethod
    def detect(cls, logFile):
        regex = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*(\d+.\d+.\d+.\d+)\s*S=\s*(\S*)\s*\W(\S*)\s*--\s*(.*)')

        lineNo = logFile.tell()  # Get the current file position
        line = logFile.readline()
        logFile.seek(lineNo)

        if regex.match(line):
            return True
        else:
            return False

    def __init__(self):
        super().__init__()

    def translateLine(self, ln):
        """Translate an individual line of a log file into the common log output format.  If the line does
		   not match, return None to avoid writing anything to the output file.  Should be overridden."""
        return ln


# From NCM Status->System Logs when logged in locally
class RouterUIExportTranslator(LogTranslator):
    """Translator for log files exported from router UI "Export Log" button"""
    REGEX = re.compile(r'(\S{3} \S{3} \d{2} \d{2}:\d{2}:\d{2} \d{4})\|([A-Z]*)\|([A-Za-z0-9_:\[\].]*)\|(.*)')

    def __init__(self):
        super().__init__()

    @classmethod
    def detect(cls, logFile):
        lineNo = logFile.tell()  # Get the current file position
        line = logFile.readline()
        logFile.seek(lineNo)  # Restore the file pointer

        if RouterUIExportTranslator.headerPresent(logFile) or RouterUIExportTranslator.REGEX.match(line):
            return True
        else:
            return False

    @classmethod
    def headerPresent(cls, logFile):
        """
		   Utility function to determine if the log file begins with the header at the start of the router log exported
		   by the router UI.  Sample header:
				Firmware Type: RELEASE
				Firmware Version: 7.0.10.2728fcc
				Firmware Build Date: Tue Nov 27 02:00:56 UTC 2018
				Product Name: IBR900LP6
		  """
        regexes = [r'Firmware Type: \S*',
                   r'Firmware Version: \S*',
                   r'Firmware Build Date: \S{3} \S{3}\s*\d{1,2} \d{2}:\d{2}:\d{2} \S{3} \d{4}',
                   r'Product Name: \S*']
        lineNo = 0

        logFile.seek(0)  # Go back to start of file.

        while lineNo < 4:
            line = logFile.readline()
            reg = re.compile(regexes[lineNo])
            if not reg.match(line):
                logFile.seek(0)  # Restore the file pointer.
                return False
            lineNo += 1
        # If we get here and have matched all of the items, this sure appears to be a Router UI
        return True

    def translateLine(self, ln):
        """Translate a Log file from the router UI.  Basically, parse the log, transform lines to our desired format &
		   return for writing to the file."""
        mtch = RouterUIExportTranslator.REGEX.match(ln)
        if mtch:
            timestamp_str = mtch.group(1)
            if int(timestamp_str[20:24]) > 1970:
                level = mtch.group(2)
                source = mtch.group(3)
                msg = mtch.group(4)
                ip = '0.0.0.0'  # The log file doesn't have the IP.  Supply one.

                timestamp = datetime.strptime(timestamp_str, '%a %b %d %H:%M:%S %Y')
                return self.writeOutputLine(timestamp.strftime(self.OUTPUT_DATE_FORMAT), ip, level, source, msg)
            else:
                return None
        else:
            # This line doesn't match.  Don't return any text.
            return None


# I'm not sure what to call this, since I don't know where the log it translates originates from.
# Works on WigleyPumpStation log in Router_Logs
class OtherTranslater(LogTranslator):
    REGEX = re.compile(r'(\w{3}\s+\d+ \d+:\d+:\d+) (\d+\.\d+\.\d+\.\d+)\s*.'
                       r'(\w+:\s*[()a-zA-Z.:0-9_]*\s*\S*\s*\S*)[:=](.*)')

    def __init__(self):
        super().__init__()

    @classmethod
    def detect(cls, logFile):
        lineNo = logFile.tell()  # Get the current file position
        line = logFile.readline()
        logFile.seek(lineNo)  # Restore the file pointer

        if OtherTranslater.REGEX.match(line):
            return True
        else:
            return False

    def translateLine(self, ln):

        mtch = OtherTranslater.REGEX.match(ln)
        if mtch:
            timestamp_str = mtch.group(1) + " " + str(datetime.today().year)
            ip = mtch.group(2)
            level = "INFO"
            source = mtch.group(3)
            if ": " in source:
                source = source.replace(": ", ":")
            msg = mtch.group(4)
            if msg[0] == ' ':
                msg = msg[1:]

            timestamp = datetime.strptime(timestamp_str, '%b %d %H:%M:%S %Y')

            return self.writeOutputLine(timestamp.strftime(self.OUTPUT_DATE_FORMAT), ip, level, source, msg)
        else:
            # This line doesn't match.  Don't return any text.
            return None


class NCMSupportLogTranslator(LogTranslator):
    """Translator for log files exported from NCM "Export" method"""

    def __init__(self):
        super().__init__()
        # State variables
        self._lastDate = None
        self._offsetDate = None
        self._lastCorrectDate = None

    @classmethod
    def detect(cls, logFile):
        lineNo = logFile.tell()
        logFile.seek(0)
        for i in range(2):
            logFile.readline()
        line = logFile.readline()
        # Restore the line number
        logFile.seek(lineNo)
        return line == "ECM Info\n"

    def translateLine(self, ln):
        ncm_rgx = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\|\s*(\S*)\|\s*(\S*)\|(.*)$'
        #   (           Date                    ) | (Level) | (Source)|(Message)

        matchobj = re.match(ncm_rgx, ln)
        if matchobj:
            curdatetime = datetime.strptime(matchobj.group(1), self.OUTPUT_DATE_FORMAT)

            # This stuff gets kinda janky, but it's a functioning first pass for dealing with the 1969 issue
            if not self._offsetDate and curdatetime.year == 1969:  # Save last correct date
                self._offsetDate = curdatetime
                self._lastCorrectDate = self._lastDate
            if curdatetime.year == 1969:
                finaldatetime = self._lastCorrectDate - (self._offsetDate - curdatetime)
                strDateTime = finaldatetime.strftime(self.OUTPUT_DATE_FORMAT)
            else:
                self._lastDate = curdatetime
                strDateTime = matchobj.group(1)

            return self.writeOutputLine(strDateTime, '0.0.0.0', matchobj.group(2), matchobj.group(3),
                                        matchobj.group(4))

        # if ln == 'Status\n':
        # self._abortParse = True

        return None


class USBLogTranslator(LogTranslator):
    """Translator for logs collected via USB.
        They have an annoying 'record separator' character (0x1E) at the end of each line
        Also not sure what the timestamp on each line represents. Uptime?"""
    REGEX = re.compile(r'(\d+)\s*([a-z.]+)\s*([A-Za-z0-9_:\[\].]+)\s*(.+)\x1E\n')

    #       (date?) (source)  (level) (message)

    def __init__(self):
        super().__init__()

        self.baseDate = datetime.strptime('1969-12-31 18:00:00', self.OUTPUT_DATE_FORMAT)
        self.logStartTime = None

    @classmethod
    def detect(cls, logFile):
        lineNo = logFile.tell()  # Get the current file position
        line = logFile.readline()
        logFile.seek(lineNo)  # Restore the file pointer

        if USBLogTranslator.REGEX.match(line):
            return True
        else:
            return False

    def transformTimestamp(self, time):
        if self.logStartTime is None:
            self.logStartTime = int(time)

            retTime = self.baseDate
        else:
            diff = int(time) - self.logStartTime

            retTime = self.baseDate + timedelta(seconds=diff)

        return retTime.strftime(self.OUTPUT_DATE_FORMAT)

    def translateLine(self, ln):
        mtch = USBLogTranslator.REGEX.match(ln)
        if mtch:
            timestamp_str = self.transformTimestamp(mtch.group(1))
            level = mtch.group(2)
            source = mtch.group(3)
            msg = mtch.group(4)
            ip = '0.0.0.0'  # The log file doesn't have the IP.  Supply one.

            if source.endswith(':'):
                source = source[:-1]

            return self.writeOutputLine(timestamp_str, ip, level, source, msg)
        else:
            # This line doesn't match.  Don't return any text.
            return None


# From NCM System->Administration->System Logging OR System->Diagnostics->Collect Support Log (They are the same)
# Also translates internal router serial port logs
# Will not log any data before the time is set.
class LocalUISystemLogTranslator(LogTranslator):
    REGEX = re.compile(r'^(\d{2}:\d{2}:\d{2}\s*\w{2})\s*([A-Z]+)\s*([A-Za-z0-9_:\[\].]+)\s*(.+)\n')
    #                               (Time)               (Level)         (Source)         (Message)
    time_regex = re.compile(r'(\d+:\d+:\d+\s+\w+).*to:\s(\d+:\d+:\d+)\s*(\d+/\d+/\d+)\s*(\w+)')

    #                           (local time)         (Time)           (Date)      (Timezone)

    def __init__(self):
        super().__init__()
        # State variables
        self._basedate = None
        self._next_day_flag = 0

    @classmethod
    def detect(cls, logFile):
        lineNo = logFile.tell()
        flag = False
        logFile.seek(0)
        while True:
            line = logFile.readline()
            if LocalUISystemLogTranslator.REGEX.match(line):
                flag = True
                # print(line)
                break
            if line == '':
                break
        logFile.seek(lineNo)
        if flag:
            return True
        else:
            return False

    # Log entry times are in local time, but the system time is UTC. Gotta convert
    def setbasetime(self, time):
        timestamp = datetime.strptime(time.group(3) + ' ' + time.group(2) + ' ' + time.group(4), "%m/%d/%y %H:%M:%S %Z")
        self._basedate = utc_to_local(timestamp)

    # Transform time portion of the line and account for date (since this info is only present once in the entire log)
    def transformtimestamp(self, time):
        # Convert to 24 hour time
        if time[9:11] == 'PM' and time[0:2] != '12':
            time = "{}{}".format(int(time[0:2]) + 12, time[2:])
        if time[9:11] == 'AM' and time[0:2] == '12':
            time = "0{}{}".format(int(time[0:2]) - 12, time[2:])
        # Detect if it is the next day
        if int(time[0:2]) < self._basedate.hour and self._next_day_flag == 0:
            self._basedate = self._basedate + timedelta(days=1)
            self._next_day_flag = 1
        elif int(time[0:2]) > int(self._basedate.hour):
            self._next_day_flag = 0

        # combine base date, which is updated as days change, and current line time
        timestamp = datetime.combine(self._basedate.date(),
                                     datetime.strptime(time, "%H:%M:%S %p").time(), self._basedate.tzinfo)
        return timestamp.strftime(self.OUTPUT_DATE_FORMAT)

    def translateLine(self, ln):
        mtch = LocalUISystemLogTranslator.REGEX.match(ln)
        if mtch:
            time_mtch = LocalUISystemLogTranslator.time_regex.match(ln)
            if time_mtch:
                self.setbasetime(time_mtch)
            if self._basedate:
                timestamp_str = self.transformtimestamp(mtch.group(1))
            else:
                # The case where a base time isn't available (usually partial log) so an arbitrary one is set
                if LocalUISystemLogTranslator.REGEX.match(ln):
                    if not self._basedate:
                        time_mtch = LocalUISystemLogTranslator.time_regex.match(
                            "{} INFO clock System time set to: {} 04/25/19 UTC".format(ln[0:11], ln[0:8]))
                        self.setbasetime(time_mtch)
                    if self._basedate:
                        timestamp_str = self.transformtimestamp(mtch.group(1))
                else:
                    return None
            level = mtch.group(2)
            source = mtch.group(3)
            msg = mtch.group(4)
            ip = '0.0.0.0'  # The log file doesn't have the IP.  Supply one.

            if source.endswith(':'):
                source = source[:-1]

            return self.writeOutputLine(timestamp_str, ip, level, source, msg)
        else:
            return None


class CSVLogTranslator(LogTranslator):
    """Translator for logs with a comma separated value format"""
    REGEX = re.compile(r'^(\d{4}-\d{2}-\w{5}:\d{2}:\d{2}[\+-][0-9:]+)[, ]([A-Z]+)[, ]([A-Za-z0-9_:\[\].]+)[, ](.+)\n')

    def __init__(self):
        super().__init__()

        self.baseDate = None
        self.logStartTime = None

    @classmethod
    def detect(cls, logFile):
        lineNo = logFile.tell()
        flag = False
        logFile.seek(0)

        while True:
            line = logFile.readline()
            if CSVLogTranslator.REGEX.match(line):
                flag = True
                break
            if line == '':
                break
        logFile.seek(lineNo)
        if flag:
            return True
        else:
            return False

    def translateLine(self, ln):
        mtch = CSVLogTranslator.REGEX.match(ln)
        if mtch:
            timestamp_str = "{} {}".format(mtch.group(1)[0:10], mtch.group(1)[11:19])
            if int(timestamp_str[0:4]) > 1970:
                level = mtch.group(2)
                source = mtch.group(3)
                msg = mtch.group(4)
                if msg[0] == '"':
                    msg = msg[1:-1]
                ip = '0.0.0.0'  # The log file doesn't have the IP.  Supply one.
                if source.endswith(':'):
                    source = source[:-1]
                return self.writeOutputLine(timestamp_str, ip, level, source, msg)
            else:
                return None
        else:
            return None


class LogFile(object):
    def __init__(self, lfName):
        self.logFileName = lfName
        self._fileFormat = None
        self._sourceFD = None
        self._tempFileName = None
        self._tempFD = None
        self._iterMode = 'raw'
        self._translator = None

    def __iter__(self):
        return self

    def __next__(self):
        # Get next line
        line = self.getNextLine()
        if line:
            if self._iterMode == 'raw':
                return line
            elif self._iterMode == 'tokenize':
                return self._tokenize(line)
            else:
                raise Exception('Unrecognized Iterator Mode')
        else:
            raise StopIteration

    def _translateFile(self):
        # For now, just read source & write to temp all at once.  Ver 2 - produce on-demand.
        self._autoDetectFormat()
        ln = self._sourceFD.readline()

        while ln:
            translated_line = self._translator.translateLine(ln)
            if translated_line is not None:
                self._tempFD.write(translated_line)

            if self._translator.abort:
                break

            ln = self._sourceFD.readline()

        self.reset()

    def _tokenize(self, line):
        """Break line into its component parts.
		   Return:  dictionary with the following elements:  timestamp, IP, Host, Level, Source, Message"""
        ret = {}
        expr = re.compile(
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s*(\d+.\d+.\d+.\d+)\s*S=\s*(\S*)\s*\W(\S*)\s*--\s*(.*)')

        mtch = expr.match(line)
        if mtch:
            ret['timestamp'] = mtch.group(1)
            ret['ip'] = mtch.group(2)
            ret['level'] = mtch.group(3)
            ret['source'] = mtch.group(4)
            ret['message'] = mtch.group(5)

        else:
            # This line didn't match our standard format.  Advance to the next line
            ret = self.__next__()

        return ret

    def _autoDetectFormat(self):
        # If a new translator is created, it needs to be added here
        logFileTranslators = [SyslogTranslator,  # Syslog listener as produced by WANTester
                              RouterUIExportTranslator,  # Log file exported from router UI
                              NCMSupportLogTranslator,  # NCM Support log
                              USBLogTranslator,  # USB Log file
                              LocalUISystemLogTranslator,  # Internal Serial Port Log file and local NCM output
                              CSVLogTranslator,
                              OtherTranslater]  # Not sure the flavor of this log file, but it exists

        for trans in logFileTranslators:
            if trans.detect(self._sourceFD):
                self._translator = trans()
                # To ensure using correct function
                # print("parsed using: {}".format(self._translator))
                break

        if self._translator is None:
            raise Exception('Unrecognized File Format')

    def setIterMode(self, mode):
        if mode.lower() not in ['raw', 'tokenize']:
            raise Exception('Unrecognized Iterator Mode.  Should be "raw" or "tokenize"')

        self._iterMode = mode.lower()

    def open(self, keep=False):
        # open input file, read contents and modify to generic and write to new (temp) file.
        self._sourceFD = open(self.logFileName, 'r')
        if keep:
            self._tempFD = open("common_{}".format(self.logFileName.split("/")[-1]), 'w+')
        else:
            self._tempFD = tempfile.NamedTemporaryFile(mode='w+')
        self._tempFileName = self._tempFD.name

        # Translate the file now that we've opened it.
        self._translateFile()
        return

    def reset(self):
        # reset file pointer to beginning, and reset Iterator mode.
        self._tempFD.seek(0)
        self.setIterMode('raw')

    def getNextLine(self):
        # return next line from the file
        return self._tempFD.readline()

    def close(self):
        # close log file -- automatically deletes tmp file??
        self._tempFD.close()


class UniversalParser(object):
    """Universal Parser object. This is where a large chunk of processing occurs.
       This will read the common log file format that was created earlier in the process
       and generate the resulting concise file"""

    timeformat = r'%Y-%m-%d %H:%M:%S'
    # excellent = if greater or equal to [0],
    # good = if greater than [1] but less than [0]
    # fair = if greater than [2] but less than [1],
    # poor = if less than [2]
    rssi = [-67, -70, -80]
    sinr = [20, 13, 0]
    rsrp = [-80, -90, -100]
    rsrq = [-10, -15, -20]
    ecio = [-6, -10, -20]

    reset_match = 0

    def __init__(self, debug=False):
        self.debug = debug
        pass

    def getdebug(self):
        return self.debug

    class WanEvent:
        """Contains all Connection state data and methods"""

        def __init__(self, dt, uid, state, details=None):
            if details is None:
                details = {}
            self.dt = datetime.strptime(dt, UniversalParser.timeformat)
            self.dtstr = dt
            self.uid = uid
            self.state = state  # state as string
            self.details = copy(details)  # Dictionary of additional event details
            # self.details.update({'State': state})

        def detailFormat(self):
            ret = ''
            for key in self.details:
                ret += '{}: {}, '.format(key, self.details[key])
            if ret:
                ret = ret[:-2]
            return ret

        # Keep this function in sync with getCSV
        @staticmethod
        def getCSVHeader():
            return 'datetime,uid,stateEnum,details\n'

        def getCSV(self):
            return '{},{},{},"{}"\n'.format(self.dt, self.uid, self.state, self.details)

        def getList(self):
            return [self.dt, self.state, self.detailFormat(), self.dtstr]

    class SignalEvent:
        """Contains all signal quality data and methods"""

        def __init__(self, dt, uid, rssi=None, sinr=None, rsrp=None, rsrq=None, ecio=None, band=None):
            self.dt = datetime.strptime(dt, UniversalParser.timeformat)
            self.dtstr = dt
            self.uid = uid
            self.rssi = rssi
            self.sinr = sinr
            self.rsrp = rsrp
            self.rsrq = rsrq
            self.ecio = ecio
            self.band = band

        @staticmethod
        def getCSVHeader():
            return 'datetime,uid,RSSI,SINR,RSRP,RSRQ,ECIO,BAND\n'

        def getCSV(self):
            return '{},{},{},{},{},{},{},{}\n'.format(self.dt, self.uid, self.rssi,
                                                      self.sinr, self.rsrp, self.rsrq, self.ecio, self.band)

        def getList(self):
            return [self.dt, self.rssi, self.sinr, self.rsrp, self.rsrq, self.ecio, self.band]

    class ResetEvent:

        def __init__(self, regex=None, reason=None):
            self.regex = regex
            self.reason = reason

    @classmethod
    def _parseReset(cls, line):
        """Return information if a 'reset' type event is detected. This also attempts to determine the reason
                    that this reset event occurred"""
        regexes = [
            r'^(\d*-\d*-\d* \d*:\d*:\d*).*WAN:(.*) -- Resetting$',
            r'^(\d*-\d*-\d* \d*:\d*:\d*).*cp_stack_mgr -- (.*):.*Device hard reset, hub (.*)$',
            r'(\d*-\d*-\d* \d*:\d*:\d*).*usb (.*): USB disconnect, device number (.*)$'
        ]
        for index, regex in enumerate(regexes):
            matchobj = re.match(regex, line)
            if matchobj:
                if index == 0:
                    UniversalParser.reset_match = 1
                    return cls.ResetEvent(regex)
                elif index == 1:
                    if UniversalParser.reset_match == 0:
                        UniversalParser.reset_match = 2
                        return cls.ResetEvent(regex)
                    if UniversalParser.reset_match == 1:
                        return cls.ResetEvent(regex)
                    if UniversalParser.reset_match == 3:
                        UniversalParser.reset_match = 0
                        return cls.ResetEvent(regex, 'Modem/hardware initiated reset(possible crash)')
                elif index == 2:
                    if UniversalParser.reset_match == 0:
                        UniversalParser.reset_match = 3
                        return cls.ResetEvent(regex)
                    if UniversalParser.reset_match == 1:
                        UniversalParser.reset_match = 0
                        return cls.ResetEvent(regex, 'User initiated reset')
                    if UniversalParser.reset_match == 2:
                        UniversalParser.reset_match = 0
                        return cls.ResetEvent(regex, 'Driver initiated reset')

    # Given a line, return a WANEvent if the line shows one
    # Example lines. Parse out time, uid, last state, new state, reason (if given)
    # 2019-04-19 03:37:05 192.168.0.1 S= INFO ﻿WAN:685ca069 -- connecting -> disconnecting
    # 2019-04-19 03:35:51 192.168.0.1 S= INFO ﻿WAN:686be2ac -- connecting -> connected, Reason: Failback
    @classmethod
    def _parseDevState(cls, line, debug):
        retEvt = None
        rgxDevState = r'^(\d*-\d*-\d* \d*:\d*:\d*).*WAN:(.*) -- (?!Service Change)(.*) -> (.*?)(?:, Reason: (.*))?$'
        matchobj = re.match(rgxDevState, line)
        if matchobj:
            time = matchobj.group(1)
            uid = matchobj.group(2)
            # When log file has debug lines, the same uid has subheaders. Exclude these by default
            if '.' in uid and not debug:
                return None
            state = matchobj.group(4)
            prevstate = matchobj.group(3)
            reason = matchobj.group(5)
            # details = {'PrevState': prevstate}
            if reason:
                details = {'Reason': reason}
            else:
                details = {'PrevState': prevstate}
            retEvt = cls.WanEvent(time, uid, state, details)
        return retEvt

    @classmethod
    def _parseUnplug(cls, line):
        retEvt = None
        rgxUnplug = r'^(\d*-\d*-\d* \d*:\d*:\d*).*WAN:(.*) -- Unplugged$'
        matchobj = re.match(rgxUnplug, line)
        if matchobj:
            time = matchobj.group(1)
            uid = matchobj.group(2)
            state = "unplugged"
            retEvt = cls.WanEvent(time, uid, state)
        return retEvt

    @classmethod
    def _parsePlug(cls, line):
        retEvt = None
        rgxPlug = r'^(\d*-\d*-\d* \d*:\d*:\d*).*WAN:(.*) -- Plug event: ok$'
        matchobj = re.match(rgxPlug, line)
        if matchobj:
            time = matchobj.group(1)
            uid = matchobj.group(2)
            state = "plugged"
            if int(time[:4]) > 1970:
                retEvt = cls.WanEvent(time, uid, state)
        return retEvt

    @classmethod
    def _parseConfigure(cls, line):
        retEvt = None
        rgxConfig = r'^(\d*-\d*-\d* \d*:\d*:\d*).*WAN:(.*) -- Configure Event:(.*)$'
        matchobj = re.match(rgxConfig, line)
        if matchobj:
            time = matchobj.group(1)
            uid = matchobj.group(2)
            state = "configure"
            details = {'Reason': matchobj.group(3)}
            if int(time[:4]) > 1970:
                retEvt = cls.WanEvent(time, uid, state, details)
        return retEvt

    # Given a line return a SignalEvent with all relevant info
    @classmethod
    def _parseSignalQuality(cls, line):
        """Detect signal quality log lines and interpret the data that is in them. The bounds for what determines
        'Good', 'Poor', etc. are at the top of this class."""
        retEvt = None
        time = None
        uid = None
        rgx_signal_quality = r'^(\d*-\d*-\d* \d*:\d*:\d*).*WAN:(.*) -- \S*\s*signal(.*)'
        re_end_str = r'{}:(.*)'  # RF band doesn't have parens
        re_gen_sig_str = r'{}:(.*?)[\( ]'  # signal strings in middle of line all have the form: XXXX:<val>(unit)

        sig_strs = {
            # 'RFBAND':[re_end_str, None],
            'RSSI': [re_gen_sig_str, cls.rssi],
            'SINR': [re_gen_sig_str, cls.sinr],
            'RSRP': [re_gen_sig_str, cls.rsrp],
            'RSRQ': [re_gen_sig_str, cls.rsrq],
            'ECIO': [re_gen_sig_str, cls.ecio],
            'RFBAND': [re_end_str, None]
        }
        retDict = {
            'rssi': {"RSSI": (None, None)},
            'sinr': {"SINR": (None, None)},
            'rsrp': {"RSRP": (None, None)},
            'rsrq': {"RSRQ": (None, None)},
            'ecio': {"ECIO": (None, None)},
            'rfband': {"RFBAND": None}
        }
        matchobj = re.match(rgx_signal_quality, line)
        if matchobj:
            for sig_str in sig_strs:
                time = matchobj.group(1)
                uid = matchobj.group(2)
                search_str = sig_strs[sig_str][0].format(sig_str)
                match_str = re.search(search_str, matchobj.group(3), flags=0)
                if not match_str:
                    continue
                val = match_str.group(1)
                if sig_str == 'RSSI' and val == '0':
                    val = '-125'
                limits = sig_strs[sig_str][1]
                if not limits:
                    retDict[sig_str.lower()] = {sig_str: val}
                    continue
                val_int = float(val)
                if val_int >= limits[0]:
                    quality = "Excellent"
                elif val_int >= limits[1]:
                    quality = "Good"
                elif val_int >= limits[2]:
                    quality = "Fair"
                else:
                    quality = "Poor"

                retDict[sig_str.lower()] = {sig_str: (val_int, quality)}

            retEvt = cls.SignalEvent(time, uid, retDict['rssi'], retDict['sinr'],
                                     retDict['rsrp'], retDict['rsrq'], retDict['ecio'], retDict['rfband'])
        return retEvt

    @classmethod
    def _parseOtherRegEx(cls, line, extra_regexes=None):
        """Captures ERROR level events and any line not starting with a number (usually detail lines relating to errors)
           Add any other regular expressions that should always be put in concise log file here"""
        # Add any extra regular expressions passed to the function
        if extra_regexes:
            for extra in extra_regexes:
                matchobj = re.search(extra, line)
                if matchobj:
                    return True
        return False

    # Main parsing funcion
    # Given file name parse it and return the specified format
    # First output is Signal Quality data, Second is Connection State data
    # Output is {uid:[[time,state,details],],}
    @classmethod
    def parseLog(cls, log, extra_args):
        retTypes = ['dict', 'csv', 'plot', 'json']
        error_regexes = [r'^(\d*-\d*-\d* \d*:\d*:\d*).*ERROR (.*) -- (.*):(.*)',
                         r'^[^0-9].*']
        if extra_args['format'] not in retTypes:
            raise ValueError(' retType must be in {}'.format(retTypes))
        # Every function in list below will be executed on every line
        # Every function will return either WanEvent or SignalEvent, which have the same methods
        parseFuncs = [cls._parseDevState, cls._parseUnplug, cls._parsePlug, cls._parseConfigure,
                      cls._parseSignalQuality, cls._parseReset, cls._parseOtherRegEx]
        log.reset()
        retConnCSV = cls.WanEvent.getCSVHeader()  # Start building string of all parsed data in CSV output format
        retSigCSV = cls.SignalEvent.getCSVHeader()
        retSigDict = {}
        retConnDict = {}
        line_num = 1
        flag = 0
        linedate = None
        evt = None
        for line in log:
            if '0' < line[0] < '9':
                linedate = datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S')
            if linedate and extra_args['date_range'][0] < linedate < extra_args['date_range'][1]:
                for func in parseFuncs:
                    if func == cls._parseDevState:
                        evt = cls._parseDevState(line, extra_args['debug'])
                    elif func == cls._parseOtherRegEx and (extra_args['error_logging'] or extra_args['extra_regex']):
                        if extra_args['error_logging'] and not flag:
                            flag = 1
                            for extra in error_regexes:
                                extra_args['extra_regex'].append(extra)
                        evt = cls._parseOtherRegEx(line, extra_args['extra_regex'])
                    elif func != cls._parseOtherRegEx:
                        evt = func(line)
                    if evt:  # If evt not None, we've got a new event to add
                        extra_args['fd_concise'].write("{} - {}".format(line_num, line))
                        if func == cls._parseReset or func == cls._parseOtherRegEx:
                            break
                        if extra_args['format'] == 'csv':  # Building CSV output
                            if func == cls._parseSignalQuality:
                                retSigCSV += evt.getCSV()
                            else:
                                retConnCSV += evt.getCSV()
                        if extra_args['format'] in ['dict', 'plot', 'json']:  # Here we're building dictionary output
                            if func == cls._parseSignalQuality:
                                if evt.uid not in retSigDict:
                                    retSigDict[evt.uid] = []
                                retSigDict[evt.uid].append(evt.getList())
                            else:
                                if evt.uid not in retConnDict:
                                    retConnDict[evt.uid] = []
                                retConnDict[evt.uid].append(evt.getList())
                            break
            line_num += 1
        log.reset()
        # Return format
        if extra_args['format'] == 'json' or extra_args['format'] == 'plot':
            return json.dumps(retSigDict, default=format_dt), json.dumps(retConnDict, default=format_dt)
        if extra_args['format'] == 'csv':
            return retSigCSV, retConnCSV
        if extra_args['format'] == 'dict':
            return retSigDict, retConnDict


def generate_data(data, fileout=True, fd=None):
    """Generates the data file if an output format with a data file has been specified in the command line"""
    # data:
    #  {
    #      uid1:{'RSSI':[], 'SINR':[], 'RSRP':[], 'RSRQ':[], 'ECIO':[], 'RFBAND':[]}
    #      uid2:{'RSSI':[], 'SINR':[], 'RSRP':[], 'RSRQ':[], 'ECIO':[], 'RFBAND':[]}
    #  }
    if isinstance(data[0], dict):
        for uid in data:
            for series in uid:
                if fileout:
                    fd.write("Series, name: {}\n".format(series))
                else:
                    print("Series, name: {}".format(series))
                series_data = uid[series]
                if isinstance(series_data, dict):
                    for sd in series_data:
                        if fileout:
                            fd.write("  sub name: {}\n".format(sd))
                        else:
                            print("  sub name: {}".format(sd))

                        for s in series_data[sd]:
                            if fileout:
                                fd.write("    {}\n".format(s))
                            else:
                                print("    {}".format(s))

                else:
                    for sd in series_data:
                        if fileout:
                            fd.write("  data: {}\n".format(sd))
                        else:
                            print("  data: {}".format(sd))
    else:
        if fileout:
            fd.write(data[0])
        else:
            print(data[0])


def parseall(logfile, extra_args):
    """Calls all the necessary helper functions with the correct arguments"""
    data = []
    sig = UniversalParser()
    # Parse the log with provided arguments, generates signal quality and connection state data objects
    sig_data, conn_data = sig.parseLog(logfile, extra_args)
    if extra_args["format"] == 'plot':
        data.append(sig_data)
        data.append(conn_data)
        createhtml(logfile.logFileName, data)
    else:
        data.append(sig_data)
        # Generate output data file
        generate_data(data, True, extra_args["fd_data"])
        extra_args["fd_data"].write("\n")
        data.append(conn_data)
        data.clear()
        data.append(conn_data)
        # Append connection state data to output file
        generate_data(data, True, extra_args["fd_data"])


# Creates the html file that will display the data
def createhtml(filename, data):
    html = """<!DOCTYPE html>
        <html lang="en">

          <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
            * {{
                box-sizing: border-box;
            }}
            .center {{
              margin: auto;
              width: 60%;
            }}
            header {{
              margin: 0;
              padding: 0;
              height: 150px;
              width: 100%;
              background-color: #333f47;
            }}
            header h1 {{
              margin: 0;
              padding-top: 20px;
              text-align: center;
              color: #fead00;
            }}
            html, body {{
              margin: 0;
              padding: 0;
            }}
            p {{
              text-align: center;
            }}
            table {{
                font-family: arial, sans-serif;
                border-collapse: collapse;
                width: 100%;
            }}
            td, th {{
                border: 1px solid #dddddd;
                text-align: left;
                padding: 8px;
            }}
            tr:nth-child(even) {{
                background-color: #dddddd;
            }}
            </style>
          </head>

          <body onload="processFile(0, 1)">

            <header>
        <h1 id="filename">{}</h1>
        <h1>Signal Quality and Connection State</h1>
            </header>
            <button onclick="Open()">Click me</button>
            <div id="choose_file"; style="text-align: center">
              Choose a different file to plot 
              <input type='file' accept='.json' onchange='setStorage(event), renameLogFile(event)'>
              (Must be .json file. This is produced when run with "-o json" argument)
              <br>
            </div>
            <table id="header_table">
                <tr>
                    <th>UID</td>
                    <th>Log Period</td>
                    <th>Times Unplugged</td>
                    <th>Times Disconnected</td>
                    <th>Connection Uptime</td>
                </tr>
            </table>
            <div style="width: 100%; overflow: hidden;">
              <div style="width: 50%; float: left; left: 50px;"><h2 style="text-align: center">Signal Qualities</h2>
              </div>
              <div style="margin-left: 50%;"><h2 style="text-align: center">Connection States</h2>
              </div>
            </div>

            <div style="width: 100%; overflow: hidden;">
              <div id="sigPlot" style="width: 50%; float: left; left: 50px;"></div>
              <div id="connPlot" style="margin-left: 50%;"></div>
            </div>
            <script>
            function Open() {{
                window.open("usb_log.txt.html", "_blank");
            }}
            //Will rename the title if a new file is opened
            function renameLogFile(event = 0) {{
              if(sessionStorage.getItem("title") && !event) {{
                var title = document.getElementById("filename") 
                title.innerHTML = sessionStorage.getItem("title");
              }}   
              if(event) {{
                sessionStorage.setItem("title", event.target.files[0].name);
              }}

            }}

            //reads json data from a file
            function readFileAsync(event = 0, fromload = 0) {{
              return new Promise((resolve, reject) =>{{
                let reader = new FileReader();
                reader.onload = () => {{
                  resolve(reader.result.split("\\n"));
                }};
                reader.onerror = reject;
                reader.readAsText(event.target.files[0]);
                }})
            }}
            async function setStorage(event) {{
                try {{
                  var text = await readFileAsync(event);
                  sessionStorage.setItem("text0", text[0]);
                  sessionStorage.setItem("text1", text[1]);
                  window.open(window.location.pathname, "_blank");
                }} catch (err) {{
                  console.log(err);
                }}
            }}
            //Main function, decides whether to use data in page or in file
            async function processFile(event = 0, fromload = 0) {{
              renameLogFile(event);
              //clearing divs so new data can be put in
              const sigPlotClr = document.getElementById("sigPlot");
              sigPlotClr.innerHTML = '';
              const connPlotClr = document.getElementById("connPlot");
              connPlotClr.innerHTML = '';
              if(event) {{
                try {{
                  var text = await readFileAsync(event, fromload);
                  sessionStorage.setItem("text0", text[0]);
                  sessionStorage.setItem("text1", text[1]);
                  window.open(window.location.pathname, "_blank");
                }} catch (err) {{
                  console.log(err);
                }}
              }}

              // Data in the page so that it will display on load
              if (fromload) {{
                if(sessionStorage.getItem("text0")) {{
                  var text = [sessionStorage.getItem("text0"),sessionStorage.getItem("text1")];
                  fromload = 0;  
                }}
                else {{
                    var text = [{},{}];
                }}
              }}
              var dates = [];
              var rssi_vals = [];
              var sinr_vals = [];
              var rsrp_vals = [];
              var rsrq_vals = [];
              var date_append = 0;
              var bands = [];
              var uids = [];
              var states = [];
              var reasons = [];
              const possible_states = {{
                'unplugged': 0,
                'plugged': 1,
                'configure': 2,
                'disconnected': 3,
                'disconnecting': 4,
                'standby_connecting': 5,
                'standby': 6,
                'connecting': 7,
                'connected': 8
              }};
              var index = 0;
              //choosing which data to use
              if (fromload) {{
                var sigQualObj = text[0];
                var connStateObj = text[1];
              }} else {{
                var sigQualObj = JSON.parse(text[0]);
                var connStateObj = JSON.parse(text[1]);
              }}
              //Clear header table 
              if (document.getElementById("header_table").rows.length > 1) {{
                var i;
                for (i = 1; i < document.getElementById("header_table").rows.length; i++) {{
                    document.getElementById("header_table").deleteRow(-1);
                  }}
              }}         
              //generating connection state data
              for (uid in connStateObj) {{
                uids.push(uid);
                for (entry in connStateObj[uid]) {{
                  reason_flag = 0;
                  for (value in connStateObj[uid][entry]) {{
                    if (value == 0) {{
                      dates.push(connStateObj[uid][entry][value]);
                      if (entry > 0) {{
                        if (date_append > 0 && dates[entry] == dates[entry -1].substring(0,dates[entry - 1].length - 3))
                        {{
                            date_append += .01;
                            dates[entry] = dates[entry] + date_append.toString().substring(1);
                            continue;
                          }}
                          if (dates[entry] == dates[entry - 1]) {{
                            dates[entry] = dates[entry] + '.01';
                            date_append = .01;
                            continue;
                          }}
                        }}
                        date_append = 0;
                    }}
                    if (possible_states.hasOwnProperty(connStateObj[uid][entry][value])) {{
                      states.push(possible_states[connStateObj[uid][entry][value]]);
                    }}
                    if (connStateObj[uid][entry][value].includes('Reason')) {{
                        reasons.push(connStateObj[uid][entry][value]);
                        reason_flag = 1;
                    }}
                  }}
                  if (reason_flag == 0){{
                        reasons.push('');
                    }}
                }}
                //dynamically create more divs as needed
                var div = document.createElement("div");
                div.setAttribute("id", "connPlot"+uids[index]);
                document.getElementById("connPlot").appendChild(div);
                var dates_len = dates.length - 1;
                //With NCM logs the most recent entry is at the top. 
                //This detects that and then corrects the connection state plot
                var date_front = new Date(parseInt(dates[0].substring(0,4)),
                                          parseInt(dates[0].substring(5,7)) - 1,
                                          parseInt(dates[0].substring(8,10)),
                                          parseInt(dates[0].substring(11,13)),
                                          parseInt(dates[0].substring(14,16)),
                                          parseInt(dates[0].substring(17,19)));
                var date_end = new Date(parseInt(dates[dates_len].substring(0,4)),
                                        parseInt(dates[dates_len].substring(5,7)) - 1,
                                        parseInt(dates[dates_len].substring(8,10)),
                                        parseInt(dates[dates_len].substring(11,13)),
                                        parseInt(dates[dates_len].substring(14,16)),
                                        parseInt(dates[dates_len].substring(17,19)));
                if (date_front > date_end) {{
                  var plot_shape = 'vh';
                }}
                else {{
                  var plot_shape = 'hv';
                }}
                //Plotly plot data and formatting
                var conn_trace = {{
                  x: dates,
                  y: states,
                  mode: 'lines+markers',
                  name: 'Connection State',
                  text: reasons,
                  line: {{shape: plot_shape}},
                  type: 'scatter'
                }};
                var connData = [conn_trace];
                var connLayout = {{
                  title: 'Connection State: ' + uids[index],
                  autosize: false,
                  width: 800,
                  height: 500,
                  margin: {{
                    l: 50,
                    r: 50,
                    b: 100,
                    t: 100,
                    pad: 4
                  }},
                  xaxis: {{
                    title: 'Timestamp'
                  }},
                  yaxis: {{
                    title: 'State',
                    range: [0,8.5],
                    automargin: true,
                    tickvals: Object.values(possible_states),
                    ticktext: Object.keys(possible_states)
                  }}
                }};
                Plotly.newPlot('connPlot'+uids[index], connData, connLayout,
                              {{modeBarButtonsToRemove: ['select2d',
                                                         'lasso2d',
                                                         'zoomIn2d',
                                                         'zoomOut2d',
                                                         'resetScale2d',
                                                         'toggleSpikelines',
                                                         'hoverClosestCartesian',
                                                         'hoverCompareCartesian'], displaylogo: false}});
                var state_counts = {{}};
                for (var i = 0; i < states.length; i++) {{
                  var num = states[i];
                  state_counts[num] = state_counts[num] ? state_counts[num] + 1 : 1;
                }}
                var table = document.getElementById("header_table");
                var row = table.insertRow(index+1);
                var cell1 = row.insertCell(0);
                var cell2 = row.insertCell(1);
                var cell3 = row.insertCell(2);
                var cell4 = row.insertCell(3);
                var cell5 = row.insertCell(4);
                cell1.innerHTML = uids[index];
                cell2.innerHTML = dates[0] + " - " + dates[dates.length - 1];
                if(state_counts[0] === undefined) {{
                    cell3.innerHTML = 0;
                }}
                else {{
                    cell3.innerHTML = state_counts[0];
                }}
                if(state_counts[3] === undefined) {{
                    cell4.innerHTML = 0;
                }}
                else {{
                    cell4.innerHTML = state_counts[3];
                }}
                var connected_time = 0;
                let absolute_start = new Date(dates[0]);
                let absolute_end = new Date(dates[dates.length - 1]);
                let total_time = absolute_end - absolute_start;
                for (var i = 0; i < states.length; i++) {{
                    if (states[i] == 8) {{
                        if (dates[i] != dates[dates.length - 1]) {{
                            let start_date = new Date(dates[i]);
                            let end_date = new Date(dates[i+1]);
                            connected_time += (end_date - start_date);
                        }}
                    }}
                }}
                let uptime = connected_time/total_time;
                cell5.innerHTML = (uptime * 100).toFixed(2) + "%";
                dates.length = 0;
                states.length = 0;
                reasons.length = 0;
                index += 1;
              }}
              //clearing the dates array to be used again
              dates.length = 0;
              uids.length = 0;
              index = 0;
              //Generating signal quality data
              for (uid in sigQualObj) {{
                uids.push(uid);
                for (entry in sigQualObj[uid]) {{
                  for (data_obj in sigQualObj[uid][entry]) {{
                    if (typeof sigQualObj[uid][entry][data_obj] === 'object' &&
                               sigQualObj[uid][entry][data_obj] !== null) 
                    {{
                      for (sig in sigQualObj[uid][entry][data_obj]) {{
                        if (sig == 'RSSI') {{
                          rssi_vals.push(sigQualObj[uid][entry][data_obj][sig][0]);
                        }}
                        else if (sig == 'SINR') {{
                          sinr_vals.push(sigQualObj[uid][entry][data_obj][sig][0]);
                        }}
                        else if (sig == 'RSRP') {{
                          rsrp_vals.push(sigQualObj[uid][entry][data_obj][sig][0]);
                        }}
                        else if (sig == 'RSRQ') {{
                          rsrq_vals.push(sigQualObj[uid][entry][data_obj][sig][0]);
                        }}
                        else if (sig == 'RFBAND') {{
                          bands.push(sigQualObj[uid][entry][data_obj][sig]);
                        }}
                      }}
                    }}
                    else if (sigQualObj[uid][entry][data_obj] !== null) {{
                      dates.push(sigQualObj[uid][entry][data_obj]);
                    }}
                  }}
                }}

                var div = document.createElement("div");
                div.setAttribute("id", "sigPlot"+uids[index]);
                document.getElementById("sigPlot").appendChild(div);
                //Plotly Data: 1-4 are real data, 5-8 necessary for right side y-axis describing 'poor' -> 'excellent'
                var trace1 = {{
                  x: dates,
                  y: rssi_vals,
                  text: bands,
                  mode: 'scatter',
                  name: 'RSSI'
                }};
                var trace2 = {{
                  x: dates,
                  y: sinr_vals,
                  text: bands,
                  xaxis: 'x',
                  yaxis: 'y4',
                  mode: 'scatter',
                  name: 'SINR'
                }};
                var trace3 = {{
                  x: dates,
                  y: rsrp_vals,
                  text: bands,
                  xaxis: 'x',
                  yaxis: 'y2',
                  mode: 'scatter',
                  name: 'RSRP'
                }};
                var trace4 = {{
                  x: dates,
                  y: rsrq_vals,
                  text: bands,
                  xaxis: 'x',
                  yaxis: 'y3',
                  mode: 'scatter',
                  name: 'RSRQ'
                }};
                var trace5 = {{
                  x: dates[0],
                  y: rssi_vals[0],
                  xaxis: 'x',
                  yaxis: 'y5',
                  showlegend: false,
                  mode: 'scatter'
                }};
                var trace6 = {{
                  x: dates[0],
                  y: sinr_vals[0],
                  xaxis: 'x',
                  yaxis: 'y8',
                  showlegend: false,
                  mode: 'scatter'
                }};
                var trace7 = {{
                  x: dates[0],
                  y: rsrp_vals[0],
                  xaxis: 'x',
                  yaxis: 'y6',
                  showlegend: false,
                  mode: 'scatter'
                }};
                var trace8 = {{
                  x: dates[0],
                  y: rsrq_vals[0],
                  xaxis: 'x',
                  yaxis: 'y7',
                  showlegend: false,
                  mode: 'scatter'
                }};
                var data = [trace1, trace3, trace4, trace2, trace5, trace7, trace8, trace6];
                var layout = {{
                  title: 'Signal Quality: ' + uids[index],
                  autosize: false,
                  width: 800,
                  height: 800,
                  margin: {{
                    l: 50,
                    r: 50,
                    b: 100,
                    t: 100,
                    pad: 4
                  }},
                  legend: {{
                    x: 1.1,
                    y: .5
                  }},
                  xaxis: {{
                    title: 'Timestamp'
                  }},
                  yaxis: {{
                    title: 'RSSI(dBm)',
                    range: [-130, -25]
                  }},
                  yaxis2: {{
                    title: 'RSRP(dB)',
                    zeroline: false,
                    range: [-140, -50]
                  }},
                  yaxis3: {{
                    title: 'RSRQ(dB)',
                    range: [-30, -5]
                  }},
                  yaxis4: {{
                    title: 'SINR(dB)',
                    zeroline: false,
                    range: [-20, 35]
                  }},
                  //Make sure tickvals the same as in the python script describing the signal strength cutoffs
                  yaxis5: {{
                    title: 'Quality',
                    range: [-130, -25],
                    tickvals: [-60, -70, -80, -125],
                    ticktext: ['Excellent', 'Good','Fair', 'Poor'],
                    overlaying: 'y',
                    side: 'right'
                  }},
                  yaxis6: {{
                    title: 'Quality',
                    zeroline: false,
                    tickvals: [-80, -90, -100, -140],
                    range: [-140, -50],
                    ticktext: ['Excellent', 'Good','Fair', 'Poor'],
                    overlaying: 'y2',
                    side: 'right'
                  }},
                  yaxis7: {{
                    title: 'Quality',
                    range: [-30, -5],
                    tickvals: [-10, -15, -20, -30],
                    ticktext: ['Excellent', 'Good','Fair', 'Poor'],
                    overlaying: 'y3',
                    side: 'right'
                  }},
                  yaxis8: {{
                    title: 'Quality',
                    zeroline: false,
                    tickvals: [20, 13, 0, -20],
                    range: [-20, 35],
                    ticktext: ['Excellent', 'Good','Fair', 'Poor'],
                    overlaying: 'y4',
                    side: 'right'
                  }},
                  grid: {{
                    rows: 4,
                    columns: 1,
                    subplots: [['xy'], ['xy2'], ['xy3'], ['xy4']],
                    roworder: 'top to bottom'
                  }}
                }}; // end of Layout object
                Plotly.newPlot('sigPlot' + uids[index], data, layout,
                              {{modeBarButtonsToRemove: ['select2d',
                                                         'lasso2d',
                                                         'zoomIn2d',
                                                         'zoomOut2d',
                                                         'resetScale2d',
                                                         'toggleSpikelines',
                                                         'hoverClosestCartesian',
                                                         'hoverCompareCartesian'], displaylogo: false}});
                rssi_vals.length = 0;
                sinr_vals.length = 0;
                rsrp_vals.length = 0;
                rsrq_vals.length = 0;
                dates.length = 0;
                bands.length = 0;
                index += 1;
              }} // end of sig quality loop. It's long
            }};// end of processFile()

            </script>

          </body>
        </html>
        """.format(filename, data[0], data[1])
    fd = open("{}.html".format(filename.split("/")[-1]), 'w')
    fd.write(html)
    fd.close()


if __name__ == "__main__":
    help_str = """Universal Log Parser. \n
    Parses through a log file to find relevant signal strength and connection state data and plots results. \n
    The files are created by default in the root directory, wherever UniversalLogParser is. \n
    File paths for log files can be specified. \n
    The names of the files created are data_{{filename}}, concise_{{filename}}, and {{filename}}.html. """

    # Arguments added using argparse package
    parser = argparse.ArgumentParser(description=help_str)
    parser.add_argument('filename', nargs='?', help='name of log file to parse')
    parser.add_argument('-o', default='plot', help='Output format. plot, dict, csv, or json(default plot).\n Only'
                                                   ' plot creates a webpage plot. The other options generate a data '
                                                   'file in the specified format. json outputs are plottable from the'
                                                   '"choose a different file to plot" button on the page')
    parser.add_argument('-k', default=False, action='store_const', const=True, help='Keep the common format log file. '
                                                                                    'This is useful since line numbers in the concise output refrence the common log format')
    parser.add_argument('-d', default=False, action='store_const', const=True, help='Use if there are debug lines in '
                                                                                    'the log file. Will plot more charts')
    parser.add_argument('-e', default=False, action='store_const', const=True, help='Will write error messages to '
                                                                                    'concise log file')
    parser.add_argument('--regex', default=False, action='store_const', const=True, help='Use to enter a menu '
                                                                                         'where additional regular '
                                                                                         'expressions can be supplied')
    parser.add_argument('--fromto', nargs='*', help='Specify a date and time range in the form {from} - {to}'
                                                    'Where {from} and/or {to} are of the form '
                                                    '(year)-(month)-(day) (24-hour):(minute):(second)'
                                                    'Leave one or both blank to have the range open ended: '
                                                    'MUST STILL HAVE THE DASH '
                                                    'Ex: --fromto 2019-04-24 13:03:43 - 2019-04-25 02:22:15 '
                                                    'Ex: --fromto - 2020-07-17 13:21:44')
    args = parser.parse_args()
    # Determining if the date range supplied has lower and/or upper bounds
    if args.fromto:
        if args.fromto[0] == '-':
            startdate = datetime.min
            enddate = datetime.strptime(args.fromto[1] + args.fromto[2], '%Y-%m-%d%H:%M:%S')
        else:
            startdate = datetime.strptime(args.fromto[0] + args.fromto[1], '%Y-%m-%d%H:%M:%S')
            if len(args.fromto) > 3:
                enddate = datetime.strptime(args.fromto[3] + args.fromto[4], '%Y-%m-%d%H:%M:%S')
            else:
                enddate = datetime.max
    else:
        startdate = datetime.min
        enddate = datetime.max
    print("Running...\n\n")
    if args.filename:
        logFileName = args.filename
    else:
        logFileName = input("Enter log file name: ")
    # print(logFileName)
    extra_regex = []
    # Get regexes until user is done entering
    if args.regex:
        while True:
            entry = input("Enter a regular expression to filter for or X to quit entry and continue: \n")
            if entry == 'X':
                break
            else:
                extra_regex.append(entry)
    fd_data = False
    fd_concise = False

    lf = LogFile(logFileName)
    lf.open(args.k)

    if '/' in logFileName:
        shortname = logFileName.split("/")[-1]
    else:
        shortname = logFileName
    # Only create the data file if a different output format is specified
    if args.o != 'plot':
        fd_data = open("data_{}.{}".format(shortname, args.o), 'w+')
    fd_concise = open("concise_{}".format(shortname), 'w+')
    # Create a header on the concise log file
    fd_concise.write('[Line Number in common log (use -k to keep)] - [Time][IP][Level][Source][Info]\n')
    other_args = {
        "format": args.o,
        "debug": args.d,
        "error_logging": args.e,
        "fd_data": fd_data,
        "fd_concise": fd_concise,
        "extra_regex": extra_regex,
        "date_range": [startdate, enddate]
    }
    # Begin Parsing
    parseall(lf, other_args)
    # Open the edited html file in browser
    webbrowser.open('{}.html'.format(shortname))

    lf.reset()
    lf.close()
    if fd_data:
        fd_data.close()
    fd_concise.close()
    print("Complete\n\n")
