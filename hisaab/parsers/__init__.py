from hisaab.parsers.axis import Axis_CC_Parser, AxisXLSParser
from hisaab.parsers.hdfc import HDFC_CC_Parser, HDFCXLSParser
from hisaab.parsers.icici import ICICI_CC_Parser, ICICIXLSParser

PARSERS = {
    "icici-cc": ICICI_CC_Parser(),
    "hdfc-cc": HDFC_CC_Parser(),
    "axis-cc": Axis_CC_Parser(),
    "icici": ICICIXLSParser(),
    "hdfc": HDFCXLSParser(),
    "axis": AxisXLSParser(),
}
