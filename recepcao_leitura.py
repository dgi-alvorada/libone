import onexml
import oneclient
import utils
import glob
import datetime
import re
import os
from multiprocessing import Process
import sys
import time
from pathlib import Path

#move all to the send folder to clean old ftp files
output_date = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
os.system("mkdir " + utils.sent_folder + "/" + str(output_date))
os.system("mv " + utils.new_folder + "/* " + utils.sent_folder + "/" + str(output_date))

one_ws = oneclient.WSClient(
    utils.pfx_file,
    utils.pfx_passw,
    utils.ca_file,
)

#Normal transmission as default
tsType = utils.tpTransm.Normal.value
#the camera do not detect the vehicle Type, default as Passeio
vehicleType = utils.tpVeiculo.Passeio.value

last_plate = {}

#move file to sent dir
def move_file_sent_folter(dir_and_filename, date_dir, filename):
  #'renames' remove empty dirs, .keepdir file to avoid dir deletion witch may cause write problems
  Path(utils.new_folder + date_dir + ".keepdir").touch(exist_ok=True)
  os.renames(dir_and_filename, utils.sent_folder + date_dir + filename)

def main():
  global last_plate

  while True:
    try:
      #get all photos on ftp folder
      jpgFilenamesList = glob.glob(pathname=utils.new_folder + '/**/*.jpg', recursive=True)
      jpgFilenamesList = sorted(jpgFilenamesList, key=os.path.getmtime)
      for dir_and_filename in jpgFilenamesList:
        #debug
        #print(dir_and_filename)

        #ftp file name on cam must be configured to /20%2y/%2m/%2d/%2h/%2n/id_%2s_%f_%p
        #id is the cam identifier without the left zeros configured on cam/name.ini file
        m = re.search(r'(\/([0-9]{4})\/([0-9]{2})\/([0-9]{2})\/([0-9]{2})\/([0-9]{2})\/)(([0-9]+)_([0-9]{2})_[0-9]+_(\w{7})\.jpg)$', dir_and_filename)
        #skip bad dir_and_filename
        if (m is None):
          utils.print_to_log("Error! Bad filename: " + dir_and_filename)
          m = re.search(r'\/(w+\.jpg)$', dir_and_filename)
          if (m is not None):
            move_file_sent_folter(dir_and_filename, '/bad/', m.group(1))
          continue;

        plate = m.group(10)
        date_dir = m.group(1)
        filename = m.group(7)

        #No date/ntp set generate photo names without the date with '/2000/00/00/00/00'
        #The cam may be rebooting every 10 minutes, DGT used a redundant watchdog on the cam, to disable use htttp://CAM_IP/api/config.cgi?OscOutput=2'
        if (date_dir == '/2000/00/00/00/00/'):
          mod_timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(dir_and_filename))
          photoDate = mod_timestamp.strftime("%Y-%m-%dT%H:%M:%S-03:00")
          #debug
          #print(photoDate)
          Path(utils.new_folder + date_dir + ".keepdir").touch(exist_ok=True)
          date_dir = mod_timestamp.strftime("/%Y/%m/%d/%H/%M/")
          #create the new dir if it do not exist
          os.makedirs(utils.new_folder + date_dir, exist_ok=True)
        else:
          #get photo date from ftp file name in the format %Y-%m-%dT%H:%M:%S-03:00, example 2022-11-09T13:45:40-03:00
          photoDate = m.group(2) + '-' + m.group(3) + '-' +  m.group(4) + 'T' + m.group(5) + ':' + m.group(6) + ':' + m.group(9) + '-03:00'

        cam_last_plate = last_plate.get(m.group(8))
        duplicated = False;
        if (cam_last_plate is not None):
          for l in cam_last_plate:
            if (l == plate):
              duplicated = True
              break
        #skip photo without plate or same plate as last utils.duplicated_list sent
        if (plate == "0000000" or duplicated == True):
          move_file_sent_folter(dir_and_filename, date_dir, filename)
          #debug
          '''if (duplicated == True):
            print("skip duplicated " + dir_and_filename + ' plate ' + plate)
          else:
            print("skip no plate " + dir_and_filename + ' plate ' + plate)'''
          continue;

        #15 digits id
        idEqp = m.group(8).rjust(15,'0')

        result, used_xml = one_ws.oneRecepcaoLeitura(dir_and_filename, idEqp, tsType, photoDate, plate, vehicleType)

        #debug
        #print(onexml.dump_tostring(result, xml_declaration=False, pretty_print=True))
        #print errors to log file, cStat response not utils.cstat_ok
        if (result is not None):
         rcStat = result.find('{http://www.portalfiscal.inf.br/one}cStat')
         if (rcStat is not None):
           if (rcStat.text != utils.cstat_ok):
             utils.print_to_log(onexml.dump_tostring(result, xml_declaration=False, pretty_print=True))
             utils.print_to_log(dir_and_filename + ' plate ' + plate)
           else:
             list = last_plate.get(m.group(8))
             if (list is not None):
               if (len(list) == utils.duplicated_list_size):
                 list.pop(0)
               list.append(plate)
             else:
               last_plate[m.group(8)] = [plate]
             #debug
             #print("sucess " + dir_and_filename + ' plate ' + plate)

        #debug
        #print(plate)
        #print(m.group(8))
        #print(onexml.dump_tostring(used_xml, xml_declaration=False, pretty_print=True))

        move_file_sent_folter(dir_and_filename, date_dir, filename)

      #wait seconds to look for new photos
      time.sleep(utils.pooling_time);
    except Exception as ex:
      utils.print_to_log(ex)
      #sys.exit()

if __name__ == "__main__":
  program = Process(target=main, args=())

  program.start()
