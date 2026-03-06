from hisaab.parsers.axis import AxisParser
from hisaab.parsers.hdfc import HDFCParser
from hisaab.parsers.icici import ICICIParser
from hisaab.parsers.xls import AxisXLSParser, HDFCXLSParser, ICICIXLSParser

PARSERS = {
    "icici": ICICIParser(),
    "hdfc": HDFCParser(),
    "axis": AxisParser(),
    "icici-xls": ICICIXLSParser(),
    "hdfc-xls": HDFCXLSParser(),
    "axis-xls": AxisXLSParser(),
}
