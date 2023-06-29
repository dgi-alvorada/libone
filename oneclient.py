
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
import datetime

import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.ssl_ import create_urllib3_context

import onexml
import utils

import zeep
from zeep import xsd
from zeep.transports import Transport

from lxml import etree
import datetime
import configparser
from OpenSSL import crypto
import base64
import time

#debug
#from zeep.plugins import HistoryPlugin
#history = HistoryPlugin()

ws = None
config = configparser.ConfigParser()
here = os.path.abspath(os.path.dirname(__file__))

class CustomHTTPSAdapter(HTTPAdapter):

    def __init__(self, ctx_options=None):
        self.ctx_options = ctx_options
        super(CustomHTTPSAdapter, self).__init__()

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        if self.ctx_options is not None:
            context.load_verify_locations(self.ctx_options.get('cafile'))
            with utils.encrypt_pem_file(self.ctx_options.get('cert_data'), self.ctx_options.get('key_passwd')) as pem:
                context.load_cert_chain(pem.name, password=self.ctx_options.get('key_passwd'))
        kwargs['ssl_context'] = context
        return super(CustomHTTPSAdapter, self).init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, *args, **kwargs):
        context = create_urllib3_context()
        if self.ctx_options is not None:
            context.load_verify_locations(cafile=self.ctx_options.get('cafile'))
            with utils.encrypt_pem_file(self.ctx_options.get('cert_data'), self.ctx_options.get('key_passwd')) as pem:
                context.load_cert_chain(pem.name, password=self.ctx_options.get('key_passwd'))
        kwargs['ssl_context'] = context
        return super(CustomHTTPSAdapter, self).proxy_manager_for(*args, **kwargs)

class WSClient(object):

    def __init__(self, pfx_file=None, pfx_passw=None, ca_file=None,
                 target=utils._TARGET, one_version=utils.__one_version__):
        self.ca_file = ca_file
        self.pfx_passw = pfx_passw
        self.pfx_file = pfx_file
        if pfx_file is not None:
            self.cert_data = utils.pkcs12_data(pfx_file, pfx_passw)
        else:
            self.cert_data = None
        self.one_version = one_version
        self._set_target(target)

    def connect(self, url):
        transport_session = requests.Session()
        transport_session.mount(
            'https://',
            CustomHTTPSAdapter(
                ctx_options={
                    'cert_data': self.cert_data,
                    'key_passwd': self.pfx_passw,
                    'cafile': self.ca_file,
                }
            )
        )
        ws_transport = Transport(session=transport_session)
        return zeep.Client(
            url,
            transport=ws_transport
            #debug
 #           ,plugins=[history]
        )

    def _set_target(self, target):
        str_target = str(target)
        if str_target in utils._TARGET_TPAMB:
            self.target = utils._TARGET_TPAMB[str_target]
        else:
            self.target = str_target

    def _xsd(self, which):
        version = utils.format_xsd_version(utils.__xsd_versions__[which]['version'])
        xsd_file = utils.__xsd_versions__[which]['xsd'].format(version)
        xsd_file = os.path.join(here, 'xsd', xsd_file)
        return onexml.xsd_fromfile(xsd_file)

    def validate_envelop(self, which, envelop):
        xmlschema = self._xsd(which)
        element_test = envelop
        if not isinstance(envelop, etree._ElementTree):
            element_test = etree.ElementTree(envelop)
        onexml.XMLValidate(element_test, xsd=xmlschema, one_version=self.one_version).validate()

    def _make_oneManutencaoEQP_envelop(self, camfile, oper):
        version = utils.format_xsd_version(utils.__xsd_versions__['oneManutencaoEQP']['version'])
        xmlns = 'http://www.portalfiscal.inf.br/one'
        xml_envelop = onexml.XMLHelper('oneManEQP', xmlns=xmlns, versao=version)
        #xml_envelop.add_element('', 'oneDadosMsg')
        xml_envelop.add_element('', 'tpAmb',  utils._TARGET_index)
        xml_envelop.add_element('', 'verAplic',  utils.verAplic)
        xml_envelop.add_element('', 'tpMan',  oper)
        output_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        xml_envelop.add_element('', 'dhReg', output_date)
        xml_envelop.add_element('', 'CNPJOper', utils.CNPJOper)
        config.read(camfile)
        fvalue = config.get("caminfo", "cEQP")
        xml_envelop.add_element('', 'cEQP', fvalue)
        fvalue = config.get("caminfo", "xEQP")
        xml_envelop.add_element('', 'xEQP', fvalue)
        xml_envelop.add_element('', 'cUF', utils.cUF)
        fvalue = config.get("caminfo", "tpSentido")
        xml_envelop.add_element('', 'tpSentido', fvalue)
        fvalue = config.get("caminfo", "latitude")
        xml_envelop.add_element('', 'latitude', fvalue)
        fvalue = config.get("caminfo", "longitude")
        xml_envelop.add_element('', 'longitude', fvalue)
        fvalue = config.get("caminfo", "tpEQP")
        xml_envelop.add_element('', 'tpEQP', fvalue)
        fvalue = config.get("caminfo", "xRefCompl")
        xml_envelop.add_element('', 'xRefCompl', fvalue)

        return xml_envelop.root

    def oneManutencaoEQP(self, camfile, oper):
        xml_to_send = self._make_oneManutencaoEQP_envelop(camfile, oper)
        
        #debug
        #print(onexml.dump_tostring(xml_to_send, xml_declaration=True, pretty_print=True))
        
        self.validate_envelop('oneManutencaoEQP', xml_to_send)
        # If no exception, XML is valid
        url = utils._WS_URL[self.target]['cmvManutencaoEQP']
        ws = self.connect(url)
        
        #debug
        #ws.wsdl.dump()
        #for hist in [history.last_sent, history.last_received]:
        #  print(etree.tostring(hist["envelope"], encoding="unicode", pretty_print=True))

        #oneDadosMsg
        result = ws.service.cmvManutencaoEQP(xml_to_send)
        del ws

        # result and xml_to_send is a lxml Element object
        return (result, xml_to_send)

    def _make_oneRecepcaoLeitura_envelop(self, photoFile, idEqp, tsType, photoDate, plate, vehicleType):
        version = utils.format_xsd_version(utils.__xsd_versions__['oneRecepcaoLeitura']['version'])
        #xmlns = 'http://www.esocial.gov.br/schema/lote/eventos/envio/v{}'.format(version)
        xmlns = 'http://www.portalfiscal.inf.br/one'
        xml_envelop = onexml.XMLHelper('oneRecepLeitura', xmlns=xmlns, versao=version)
        #xml_envelop.add_element('', 'oneDadosMsg')
        xml_envelop.add_element('', 'tpAmb',  utils._TARGET_index)
        xml_envelop.add_element('', 'verAplic',  utils.verAplic)
        #Tipo de transmissao - padrao - Normal
        xml_envelop.add_element('', 'tpTransm',  tsType)
        output_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S-03:00")
        xml_envelop.add_element('', 'dhTransm', output_date)
        xml_envelop.add_element('', 'infLeitura')
        xml_envelop.add_element('infLeitura', 'cUF', utils.cUF)
        xml_envelop.add_element('infLeitura', 'dhPass', photoDate)
        xml_envelop.add_element('infLeitura', 'CNPJOper', utils.CNPJOper)
        xml_envelop.add_element('infLeitura', 'cEQP', idEqp)
        xml_envelop.add_element('infLeitura', 'placa', plate)
        #Tipo de veiculo - padrao - 3 Passeio
        xml_envelop.add_element('infLeitura', 'tpVeiculo', vehicleType)
        encoded_string = photo_str = ''
        with open(photoFile, "rb") as image_file:
          encoded_string = base64.b64encode(image_file.read())
        photo_str = encoded_string.decode('utf-8')
        #minimun size accept by the webservice
        if (len(photo_str) > utils.min_photo_size):
          xml_envelop.add_element('infLeitura', 'foto', photo_str)
        else:
          if (len(photo_str) == 0):
              time.sleep(utils.pooling_time);
              encoded_string = photo_str = ''
              with open(photoFile, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
              photo_str = encoded_string.decode('utf-8')
              if (len(photo_str) > utils.min_photo_size):
                xml_envelop.add_element('infLeitura', 'foto', photo_str)
              else:
                utils.print_to_log('Bad file low size: ' + str(len(photo_str)) + ' : ' + photoFile)
                return None
          else:
              utils.print_to_log('Bad file low size: ' + str(len(photo_str)) + ' : ' + photoFile)
              return None

        return xml_envelop.root

    def oneRecepcaoLeitura(self, photoFile, idEqp, tsType, photoDate, plate, vehicleType):
        global ws
        xml_to_send = self._make_oneRecepcaoLeitura_envelop(photoFile, idEqp, tsType, photoDate, plate, vehicleType)
        if (xml_to_send is None):
          return (None, None)

        #debug
        #print(onexml.dump_tostring(xml_to_send, xml_declaration=True, pretty_print=True))

        self.validate_envelop('oneRecepcaoLeitura', xml_to_send)
        # If no exception, XML is valid

        if (ws == None):
          url = utils._WS_URL[self.target]['cmvRecepcaoLeitura']
          ws = self.connect(url)

        #debug
        #ws.wsdl.dump()
        #for hist in [history.last_sent, history.last_received]:
        #  print(etree.tostring(hist["envelope"], encoding="unicode", pretty_print=True))

        #oneDadosMsg
        result = ws.service.CMVRecepcaoLeitura(xml_to_send)

        # result and xml_to_send is a lxml Element object
        return (result, xml_to_send)

