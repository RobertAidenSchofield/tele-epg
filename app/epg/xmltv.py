import xml.etree.ElementTree as ET
from xml.dom import minidom


def format_xmltv_datetime(value):
    return value.strftime("%Y%m%d%H%M%S %z")


def prettify_xml(elem):
    """Converts an ElementTree element to a pretty-printed XML string with a DTD."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    # The first line is the xml declaration, and we want to add our DTD right after.
    xml_declaration, rest_of_xml = reparsed.toprettyxml(indent="  ").split('\n', 1)
    
    return f'{xml_declaration}\n<!DOCTYPE tv SYSTEM "xmltv.dtd">\n{rest_of_xml}'
