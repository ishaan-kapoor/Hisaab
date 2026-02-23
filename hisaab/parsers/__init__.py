from hisaab.parsers.axis import AxisParser
from hisaab.parsers.hdfc import HDFCParser
from hisaab.parsers.icici import ICICIParser

PARSERS = {
    "icici": ICICIParser(),
    "hdfc": HDFCParser(),
    "axis": AxisParser(),
}
