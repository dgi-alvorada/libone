import onexml
import oneclient
import utils
import glob
from datetime import datetime
#import datetime
import re
import os
from multiprocessing import Process
import sys
import time
from pathlib import Path

#move all to the send folder to clean old ftp files
output_date = datetime.now().strftime("%Y%m%d%H%M%S")
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
        m = re.search(r'(?P<date_dir>\/(?P<year>[0-9]{4})\/(?P<month>[0-9]{2})\/(?P<day>[0-9]{2})\/(?P<hour>[0-9]{2})\/(?P<min>[0-9]{2})\/)(?P<filename>(?P<id>[0-9]+)_(?P<seg>[0-9]{2})_[0-9]+_(?P<plate>\w{7})\.jpg)$', dir_and_filename)
        #skip bad dir_and_filename
        if (m is None):
          #Hikvision model DS-2CD4A26FWD-IZS/P using dir name Hikvision-DS-2CD4A26FWD-IZS-P and file name with cam_name + capture_time + plate
          m = re.search(r'Hikvision-DS-2CD4A26FWD-IZS-P\/(?P<filename>(?P<id>[0-9]+)_(?P<date_dir>(?P<year>[0-9]{4})(?P<month>[0-9]{2})(?P<day>[0-9]{2})(?P<hour>[0-9]{2})(?P<min>[0-9]{2}))(?P<seg>[0-9]{2})[0-9]{3}_(?P<plate>\w{3,10})\.jpg)$', dir_and_filename)

          if (m is None):
            #utils.print_to_log("Error! Bad filename: " + dir_and_filename)
            m = re.search(r'\/(\w+\.jpg)$', dir_and_filename)
            if (m is not None):
              now_str = datetime.today().strftime('/%Y/%m/%d/%H/%M')
              #create the new dir if it do not exist
              os.makedirs(utils.new_folder + '/bad/'+ now_str, exist_ok=True)
              move_file_sent_folter(dir_and_filename, '/bad/'+ now_str + '/', m.group(1))
            continue;

        plate = m.group('plate')
        date_dir = m.group('date_dir')
        filename = m.group('filename')

        #No date/ntp set generate photo names without the date with '/2000/00/00/00/00'
        #The cam may be rebooting every 10 minutes, DGT used a redundant watchdog on the cam, to disable use htttp://CAM_IP/api/config.cgi?OscOutput=2'
        if (date_dir == '/2000/00/00/00/00/'):
          mod_timestamp = datetime.fromtimestamp(os.path.getmtime(dir_and_filename))
          photoDate = mod_timestamp.strftime("%Y-%m-%dT%H:%M:%S-03:00")
          #debug
          #print(photoDate)
          Path(utils.new_folder + date_dir + ".keepdir").touch(exist_ok=True)
          date_dir = mod_timestamp.strftime("/%Y/%m/%d/%H/%M/")
          #create the new dir if it do not exist
          os.makedirs(utils.new_folder + date_dir, exist_ok=True)
        else:
          #Hikvision model DS-2CD4A26FWD-IZS/P date_dir do not contain / - adjust it
          if (date_dir.find('/') == -1 and len(date_dir) == 12 and date_dir.isnumeric()):
            date_dir = '/' + date_dir[0:4] + '/' + date_dir[4:6] + '/' + date_dir[6:8] + '/' + date_dir[8:10] + '/' + date_dir[10:12] + '/'
            #create the new dir if it do not exist
            os.makedirs(utils.new_folder + date_dir, exist_ok=True)
            os.makedirs(utils.sent_folder + date_dir, exist_ok=True)
          #get photo date from ftp file name in the format %Y-%m-%dT%H:%M:%S-03:00, example 2022-11-09T13:45:40-03:00
          photoDate = m.group('year') + '-' + m.group('month') + '-' +  m.group('day') + 'T' + m.group('hour') + ':' + m.group('min') + ':' + m.group('seg') + '-03:00'

        cam_last_plate = last_plate.get(m.group("id"))
        duplicated = False;
        if (cam_last_plate is not None):
          for l in cam_last_plate:
            if (l == plate):
              duplicated = True
              break
        #skip photo incorrect plate lenght or no plate number or same plate as last utils.duplicated_list sent
        if ( len(plate) != 7 or plate == "0000000" or duplicated == True):
          move_file_sent_folter(dir_and_filename, date_dir, filename)
          #debug
          '''if (duplicated == True):
            print("skip duplicated " + dir_and_filename + ' plate ' + plate)
          else:
            print("skip no plate " + dir_and_filename + ' plate ' + plate)'''
          continue;

        #15 digits id
        idEqp = m.group("id").rjust(15,'0')

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
             list = last_plate.get(m.group("id"))
             if (list is not None):
               if (len(list) == utils.duplicated_list_size):
                 list.pop(0)
               list.append(plate)
             else:
               last_plate[m.group("id")] = [plate]
             #debug
             #print("sucess " + dir_and_filename + ' plate ' + plate)

        #debug
        #print(plate)
        #print(m.group("id"))
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
