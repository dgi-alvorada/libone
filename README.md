# libone

Biblioteca em Python para lidar com os processos do [One](https://dfe-portal.svrs.rs.gov.br/one):

- Comunicação com o Webservices do One para serviço de recepção de leitura de placas e cadastro de equipamentos;
- Validação dos XML's;
- Conexão com o webservices com certificado tipo `A1`.

Desenvolvida a partir da biblioteca LIBeSocial - https://github.com/qualitaocupacional/libesocial, para lidar com os eventos necessários para o cercamento eletrônico no RS a partir da estrutura deixada pela DGT.

No momento só é possível utilizar assinaturas do tipo `A1` em arquivos no formato `PKCS#12` (geralmente arquivos com extensão `.pfx` ou `.p12`).

# Instalação e Configuração

Clonar este repositório:
```
git clone https://github.com/dgi-alvorada/libone
```

Entrar na pasta do repositório recém clonado:
```
> cd libone
> instalar as dependências
    requests>=2.26.0
    lxml>=4.6.3
    zeep>=4.1.0
    signxml>=2.8.2
    pyOpenSSL<19
    six>=1.11.0
> criar os arquivos de configuração das câmeras OCR na pasta cams, conforme modelo 1_1.ini na pasta
> configurar um servidor ftp para recebimento das fotos das câmeras - sugestão vsftpd
> as câmeras OCR devem gerar arquivos com a seguinte string:
  /20%2y/%2m/%2d/%2h/%2n/id_%2s_%f_%p no caso da Câmera Pumatronix ITSCAM
  Pode ser necessária uma adaptação desta string no arquivo recepcao_leitura.py caso seja outro modelo de câmera
> copiar o certificado A1 para pasta cert
> configurar os parametros no arquivo utils.py:
  new_folder - diretório do ftp
  sent_folder - diretório para fotos enviadas/processadas
  CNPJOper - CNPJ do operador/prefeitura
  pfx_file - nome arquivo do certificado A1
  pfx_passw - senha do certificado A1
  _TARGET - ambiente de homologação ou produção no webservice do One
> cadastrar os equipamentos no webservice do One:
  usando script cadastrar_eqp.sh para cadastrar todos os equipamentos da pasta cams
  ou o cadastro_eqp.py para cadastro individual
> enviar as leituras de placas para o webservice do One usando o recepcao_leitura.py
> após os testes o recepcao_leitura.py pode ser usado como um serviço para envio continuo das leituras
  
```
