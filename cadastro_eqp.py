import onexml
import oneclient
import utils
import sys
import requests

one_ws = oneclient.WSClient(
    pfx_file=utils.pfx_file,
    pfx_passw=utils.pfx_passw,
    ca_file=utils.ca_file,
)

def main():
    
    if len(sys.argv) == 3:
      try:
        cam_cfg = sys.argv[1]
        cam_oper = sys.argv[2]
        
        result, used_xml = one_ws.oneManutencaoEQP(cam_cfg, cam_oper)
        
        print(onexml.dump_tostring(result, xml_declaration=False, pretty_print=True))
        print(onexml.dump_tostring(used_xml, xml_declaration=False, pretty_print=True))

      except RuntimeError as e:
        print(str(e))

      except requests.exceptions.ConnectionError as e:
        print('Connection error: %s' % str(e))

      except KeyboardInterrupt:
        pass
    else:
        print("USAGE:")
        print("    {} ARQUIVO_CFG_CAMERA OPERACAO(1- cadastrar,2- alterar,3-desativar,4-reativar)".format(sys.argv[0]))
        print("Example:")
        print("    {} cams/3_2.ini 1".format(sys.argv[0]))

    print("")


if __name__ == "__main__":
    main()
