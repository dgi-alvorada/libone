# Copyright 2018, Qualita Seguranca e Saude Ocupacional. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import os
import types
import codecs
import json

from collections import OrderedDict

import six

from lxml import etree

import signxml

from signxml import XMLSigner

import utils

class XMLValidateError(Exception):
    def __init__(self, list_log, message='XML is invalid. {} error(s) found'):
        self.message = message.format(len(list_log))
        self.errors = [e.message for e in list_log]
        super().__init__(self.message)


class XMLValidate(object):
    """Validate a XML document against its XSD file.

    Parameters
    ----------
    xml: A lxml.etree._ElementTree object, file-like object or the XML absolute path
        An object representing the acctual XML data.
    xsd: A lxml.etree.XMLSchema object, optional
        If not provided, one will be instantiate.
    one_version: one layout version.

    """
    def __init__(self, xml, xsd=None, one_version=utils.__one_version__):
        self.xml_doc = None
        self.last_errors = None
        if isinstance(xml, etree._ElementTree):
            self.xml_doc = xml
        else:
            self.xml_doc = load_fromfile(xml)
        if xsd is None:
            self.xsd = xsd_fromdoc(self.xml_doc, one_version=one_version)
        else:
            self.xsd = xsd

    def isvalid(self):
        """Validate XML doc and returns True or False.
        """
        self.last_errors = None
        is_valid = self.xsd.validate(self.xml_doc)
        self.last_errors = self.xsd.error_log
        return is_valid

    def validate(self):
        """Validate XML doc and throw an AssertionError exception if not valid.
        """
        if not self.isvalid():
            print(self.last_errors)
            raise XMLValidateError(self.last_errors)


class XMLHelper(object):
    """Class to help create XML documents.

    Parameters
    ----------
    root_element: root tag name.
    xmlns: Standard XML namespace (xmlns).
    attrs: Same attributes like in add_element()
    """
    def __init__(self, root_element, xmlns=None, **attrs):
        self.nsmap = {}
        if xmlns is not None:
            self.nsmap = {None: xmlns}
        self.root = create_root_element(root_element, ns=self.nsmap, **attrs)
    
    def add_element(self, element_tag, tag_name, text=None, **attrs):
        return add_element(self.root, element_tag, tag_name, text=text, ns=self.nsmap, **attrs)
    

def xsd_fromfile(f):
    with codecs.open(f, 'r', encoding='utf-8') as fxsd:
        xmlschema = etree.parse(fxsd)
    return etree.XMLSchema(xmlschema)


def xsd_fromdoc(xml_doc, one_version=utils.__one_version__):
    xsd = None
    xsd_path = os.path.dirname(os.path.abspath(__file__))
    if len(xml_doc.getroot().getchildren()) > 0:
        tag = etree.QName(xml_doc.getroot().getchildren()[0].tag)
        xsd_file = os.path.join(
            xsd_path,
            'xsd',
            'v{}'.format(one_version),
            '{}.xsd'.format(tag.localname)
        )
        xsd = xsd_fromfile(xsd_file)
    return xsd


def create_root_element(root_tag, ns={}, **attrs):
    """Create a root XML element

    Parameters
    ----------
        ns: a namespace. MUST be just one name space map!!!
        attrs: keywords attributes
    """
    if len(ns) == 1:
        keys_ = [K for K in ns]
        k = keys_[0]
        root_tag = u''.join([u'{', ns[k], u'}', root_tag])
        root = etree.Element(root_tag, nsmap=ns)
    else:
        root = etree.Element(root_tag)
    if attrs:
        for attr in attrs:
            root.set(attr, utils.normalize_text(attrs[attr]))
    return root


def add_element(root, element_tag, tag_name, text=None, ns={}, **attrs):
    tag_root = None
    ns_keys = [K for K in ns]
    if element_tag:
        if len(ns) == 1:
            search_tags = element_tag.split('/')
            k = None
            if ns_keys[0] is None:
                k = ns[None]
            else:
                k = ns_keys[0]
            for i, t in enumerate(search_tags):
                 search_tags[i] = '{{{}}}{}'.format(k, t)
            element_tag = '/'.join(search_tags)
        tag_root = root.find(element_tag)
    else:
        tag_root = root
    if tag_root is not None:
        # MUST be just one name space map!!!
        if len(ns) == 1:
            k = ns_keys[0]
            tag_name = u''.join([u'{', ns[k], u'}', tag_name])
            sub_tag = etree.SubElement(tag_root, tag_name, nsmap=ns)
        else:
            sub_tag = etree.SubElement(tag_root, tag_name)
        if attrs:
            for attr in attrs:
                sub_tag.set(attr, utils.normalize_text(attrs[attr]))
        if text is not None:
            sub_tag.text = utils.normalize_text(str(text))
        return sub_tag
    return None


def dump_tofile(root, xml_file, xml_declaration=True, pretty_print=False):
    xmlstring = dump_tostring(root, xml_declaration=xml_declaration, pretty_print=pretty_print)
    fpxml = codecs.open(xml_file, 'w', encoding='utf-8')
    fpxml.write(xmlstring)
    fpxml.close()


def load_fromfile(xml_file):
    parser = etree.XMLParser(ns_clean=True)
    return etree.parse(xml_file, parser)


def load_fromstring(xmlstring):
    element = etree.XML(xmlstring)
    return etree.ElementTree(element)


def dump_tostring(xmlelement, xml_declaration=True, pretty_print=False):
    xml_header = u''
    if xml_declaration:
        if isinstance(xml_declaration, six.string_types):
            xml_header = xml_declaration
        else:
            xml_header = u'<?xml version="1.0" encoding="UTF-8"?>'
    return ''.join([xml_header, etree.tostring(xmlelement, encoding='unicode', pretty_print=pretty_print)])


def _check_attrs(tag_dict):
    attrs = None
    value = None
    nsmap = {}
    if '__ATTRS__' in tag_dict:
        if 'xmlns' in tag_dict['__ATTRS__']:
            nsmap = {None: tag_dict['__ATTRS__'].pop('xmlns')}
        attrs = tag_dict.pop('__ATTRS__')
    if '__VALUE__' in tag_dict:
        value = tag_dict.pop('__VALUE__')
    return (attrs, nsmap, value)


def recursive_add_element(root, element, nsmap_default={}):
    for ele_k in element:
        if isinstance(element[ele_k], list):
            if ele_k == '_':
                child = root
            else:
                child = add_element(root, None, ele_k, ns=nsmap_default)
            for ele_i in element[ele_k]:
                recursive_add_element(child, ele_i, nsmap_default=nsmap_default)
        elif isinstance(element[ele_k], dict):
            attrs, nsmap, value_attr = _check_attrs(element[ele_k])
            if value_attr:
                add_element(root, None, ele_k, text=value_attr, ns=nsmap or nsmap_default, **attrs if attrs else {})
            else:
                child = add_element(root, None, ele_k, ns=nsmap or nsmap_default, **attrs if attrs else {})
                recursive_add_element(child, element[ele_k], nsmap_default=nsmap_default)
        else:
            add_element(root, None, ele_k, text=element[ele_k], ns=nsmap_default)


def load_fromjson(json_obj, root=None):
    """Create an ElementTree document based on a JSON structure:
    {
        "tag_name": {
            "__ATTRS__": {
                "attribute_1": "value",
                "attribute_2": "value",
                "xmlns": "name space",
                ...
            },
            "sub_tag_name1": "value",
            "sub_tag_name2": {
                "sub_sub_tag_name": "value"
            }
            "sub_tag_name3": {
                "__ATTRS__": {
                    "attribute_1": "value"
                },
                "__VALUE__": "value"
            },
            'list_of_tags': [
                {'tag_item1': 'tag item 1 value'},
                {'tag_item2': 'tag item 2 value'}
            ]
            ...
        }
    }

    Will render:

    <tag_name attribute_1="value" attribute_2="value" xmlns="name space">
        <sub_tag_name1>value</sub_tag_name1>
        <sub_tag_name2>
            <sub_sub_tag_name>value</sub_sub_tag_name>
        </sub_tag_name2>
        <sub_tag_name3 attribute_1="value">value</sub_tag_name3>
        <list_of_tags>
            <tag_item1>tag item 1 value</tag_item1>
            <tag_item2>tag item 2 value</tag_item2>
        </list_of_tags>
    </tag_name>

    Parameters
    ----------
    json_obj : string or DictType
        A JSON string structure or a Python dictionary.
    root : etree element object
        If None, the first element in the structure will be selected.

    Returns
    -------
    etree ElementTree
    """
    if json_obj:
        if isinstance(json_obj, six.string_types):
            py_ = json.loads(json_obj, object_pairs_hook=OrderedDict)
        else:
            py_ = json_obj
        has_root = False
        root_tag = root.copy() if root else None
        nsmap = {}
        if isinstance(py_, dict):
            for k in py_:
                if root_tag is None and not has_root:
                    attrs, nsmap, value_attr = _check_attrs(py_[k])
                    root_tag = create_root_element(k, ns=nsmap, **attrs if attrs else {})
                    has_root = True
                recursive_add_element(root_tag, py_[k], nsmap_default=nsmap)
        else:
            raise ValueError('JSON structure must be an object in the first level.')
        return etree.ElementTree(root_tag)
    return None


def sign(xml, cert_data):
    signer = XMLSigner(
        method=signxml.methods.enveloped,
        signature_algorithm='rsa-sha256',
        digest_algorithm='sha256',
        c14n_algorithm='http://www.w3.org/TR/2001/REC-xml-c14n-20010315'
    )
    xml_root = None
    if not isinstance(xml, etree._ElementTree):
        xml = load_fromfile(xml)
    xml_root = xml.getroot()
    signed_root = signer.sign(xml_root, key=cert_data['key_str'], cert=cert_data['cert_str'])
    return etree.ElementTree(signed_root)


def find(element, tagname):
    ns = element.nsmap[None]
    tag_path = tagname.split('/')
    query = '/{{{ns}}}'.format(ns=ns).join(tag_path)
    return element.find('.//{{{ns}}}{query}'.format(ns=ns, query=query))


def findall(element, tagname):
    ns = element.nsmap[None]
    tag_path = tagname.split('/')
    query = '/{{{ns}}}'.format(ns=ns).join(tag_path)
    return element.findall('.//{{{ns}}}{query}'.format(ns=ns, query=query))

