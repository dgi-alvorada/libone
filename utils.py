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
import six
import tempfile
import contextlib
from datetime import datetime

from OpenSSL import crypto

from enum import Enum

from cryptography.hazmat.primitives import serialization

__one_version__ = '2.00'

__xsd_versions__ = {
    'tiposGeralONE': {
        'version': __one_version__,
        'xsd': 'tiposGeralONE_v{}.xsd',
    },
    'oneManutencaoEQP': {
        'version': __one_version__,
        'xsd': 'oneManutencaoEQP_v{}.xsd',
    },
    'retOneManutencaoEQP': {
        'version': __one_version__,
        'xsd': 'retOneManutencaoEQP_v{}.xsd',
    },
    'oneRecepcaoLeitura': {
        'version': __one_version__,
        'xsd': 'oneRecepcaoLeitura_v{}.xsd'
    },
    'retOneRecepLeitura': {
        'version': __one_version__,
        'xsd': 'retOneRecepLeitura_v{}.xsd',
    },
    'leiauteLeituraONE': {
        'version': __one_version__,
        'xsd': 'leiauteLeituraONE_v{}.xsd',
    },
}

_TARGET = 'producao'

_WS_URL = {
    'homologacao': {
        'oneManutencaoEQP': 'https://one-homologacao.svrs.rs.gov.br/ws/oneManutencaoEQP/oneManutencaoEQP.asmx?wsdl',
        'oneRecepcaoLeitura': 'https://one-homologacao.svrs.rs.gov.br/ws/oneRecepcaoLeitura/oneRecepcaoLeitura.asmx?wsdl',
    },

    'producao': {
        'oneManutencaoEQP': 'https://one.svrs.rs.gov.br/ws/oneManutencaoEQP/oneManutencaoEQP.asmx?wsdl',
        'oneRecepcaoLeitura': 'https://one.svrs.rs.gov.br/ws/oneRecepcaoLeitura/oneRecepcaoLeitura.asmx?wsdl',
        'cmvRecepcaoLeitura': 'https://cmv-ws.sefazrs.rs.gov.br/ws/cmvRecepcaoLeitura/cmvRecepcaoLeitura.asmx?wsdl',
        'cmvManutencaoEQP': 'https://cmv-ws.sefazrs.rs.gov.br/ws/cmvManutencaoEQP/cmvManutencaoEQP.asmx?wsdl',
    },
}

_TARGET_TPAMB = {
    '1': 'producao',
    '2': 'homologacao'
}

pfx_file = 'cert/.pfx'
pfx_passw = 'senhadocertificadoA1'
ca_file='cert/icp-brasilV10V11.pem'


#oneManutencaoEQP parameters
tpSentido = { 'Entrada': 'E',
              'Saida': 'S',
              'Indeterminado': 'I'
            }

#oneRecepcaoLeitura parameters

#Ajustar os diretorios conforme necessidade
# Diretorio onde sao adicionadas as fotos via ftp
new_folder='camftp'

# Diretorio em que serao movidas as fotos processadas/enviadas
sent_folder='sent'

#log file
log_file='error.log'

#main loop polling time in seconds
pooling_time = 1

duplicated_list_size = 5
cstat_ok = '103'
min_photo_size = 10

class tpTransm(Enum):
    Normal = 'N'
    Retransmissao = 'R'
    Atraso = 'A'
class tpVeiculo(Enum):
    Carga = 1
    Passageiros = 2
    Passeio = 3

#global parameters

_TARGET_index = list(_TARGET_TPAMB.keys())[list(_TARGET_TPAMB.values()).index(_TARGET)]
verAplic = "1.0"
class TpMan(Enum):
    Cadastramento = 1
    Alteracao = 2
    Desativacao = 3
    Reativacao = 4
    
#Ajustar o CNPJ da prefeitura
CNPJOper = "CNPJdaPrefeitura"

#código IBGE RS
cUF = 43

def print_to_log(line):
  output_date = datetime.now().strftime("%c: ")
  f = open(log_file,'at')
  print(output_date + str(line), file = f)
  f.close()

# one use dot for version instead of underline
def format_xsd_version(str_version):
    '''chars_to_transform = '.-'
    result_version = str_version
    for c in chars_to_transform:
        result_version = result_version.replace(c, '_')'''
    return str_version


def normalize_text(text):
    _chars = {
    #     u'>' : u'&gt;',
    #     u'<' : u'&lt;',
    #     u'&' : u'&amp;',
        u'"' : u'&quot;',
        u"'": u'&apos;'
    }
    for c in _chars:
        text = text.replace(c, _chars[c])
    return text


def pkcs12_data(cert_file, password):
    if six.PY3:
        password = password.encode('utf-8')
    with open(cert_file, 'rb') as fp:
        content_pkcs12 = crypto.load_pkcs12(fp.read(), password)
    pkey = content_pkcs12.get_privatekey()
    cert_X509 = content_pkcs12.get_certificate()
    key_str = crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)
    cert_str = crypto.dump_certificate(crypto.FILETYPE_PEM, cert_X509)
    return {
        'key_str': key_str,
        'cert_str': cert_str,
        'key': pkey,
        'cert': cert_X509,
    }

@contextlib.contextmanager
def encrypt_pem_file(cert_data, cert_pass):
    crypto_key = cert_data['key'].to_cryptography_key()
    pem_pvkey_bytes = crypto_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(cert_pass.encode('utf-8'))
    )
    fp = tempfile.NamedTemporaryFile('w')
    fp.write(cert_data['cert_str'].decode('utf-8'))
    fp.write(pem_pvkey_bytes.decode('utf-8'))
    fp.flush()
    try:
        yield fp
    finally:
        fp.close()
