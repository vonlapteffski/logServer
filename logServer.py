import socket
import threading
import signal
import os
import evaParsers
from datetime import datetime
from time import sleep

workFlag = 1
globalStop = 0

class logWriteThread (threading.Thread): # log writing thread (text data)
  def __init__(self, name, parse, ip, port, packetFormat, logFileHeader, logFileHeaderLimited):
    threading.Thread.__init__(self)
    self.name = name # Name of thread
    self.parse = parse # Parsing function
    self.ip = ip # Ip to listen
    self.port = port # Port to listen
    self.packetFormat = packetFormat # String format to unpack struct
    self.logFileHeader = logFileHeader # Header of log .csv file
    self.logFileHeaderLimited = logFileHeaderLimited
    self.fileFlag = 0 # Flag of opened log file

  def unpack(self, data):
    self.parse(data, self.packetFormat)

  def run(self):
    global globalStop
    global workFlag
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.settimeout(1)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    self.sock.bind((self.ip, self.port))
    openFileTimeStamp = 0
    logPath = ''
    while (not globalStop):
      try:
        data, addr = self.sock.recvfrom(1024)
        dataToWrite, dataToWriteLimited = self.parse(data, self.packetFormat)
        #print(dataToWrite)
      except:
        continue
      if workFlag == 0: # If no log writing
          if self.fileFlag: # If log file is opened
            closeFiles(self)
      elif workFlag == 1: # If log is need to write
        if (not self.fileFlag):
          try:
            logPath = 'logs/' + datetime.now().strftime('%2y%m%d') + '_' + datetime.now().strftime('%H%M%S') + '/'
            self.logFilePath = logPath + self.name + '_ext' + '.csv'
            self.logFilePathLimited = logPath + self.name +'.csv'
            if not os.path.exists(logPath):
              try:
                os.mkdir(logPath)
                print('Created directory: ', logPath)
              except:
                print(self.name, ': error creating log directory')
                continue
            self.logFileStream = open(self.logFilePath, 'w')
            self.logFileStreamLimited = open(self.logFilePathLimited, 'w')
            openFileTimeStamp = TimestampMillisec64()
            self.fileFlag = 1
            self.logFileStream.write(self.logFileHeader + '\n')
            self.logFileStreamLimited.write(self.logFileHeaderLimited + '\n')
            print('Created files: ', self.logFilePath, ', ', self.logFilePathLimited)
          except:
            print(self.name + ": Error creating file")
        elif self.fileFlag: # If log is need to write and log file is opened
          if TimestampMillisec64() - openFileTimeStamp > 300000: # If age of log file is greater than 5 minutes
            closeFiles(self)
            continue
          try:
            self.logFileStream.write(dataToWrite + '\n')
            self.logFileStreamLimited.write(dataToWriteLimited + '\n')
          except:
            print('except: ' + self.name)
            closeFiles(self)
            continue
    closeFiles(self)
    self.sock.close()



class videoInThread (threading.Thread): # video server thread (dash cam)
  def __init__(self, name, ip, port): 
    threading.Thread.__init__(self)
    self.name = name
    self.ip = ip # Ip to listen
    self.port = port # Port to listen
    self.logFileStream = None # File stream to write log
    self.fileFlag = 0 # 1 - log file opened, 0 - log file closed
    self.connection = open('Crutch', 'w') # Network file-like object to stream data

  def openConnection(self):
    try:
      self.sock = socket.socket()
      self.sock.settimeout(1)
      self.sock.bind((self.ip, self.port))
      self.sock.listen(0)
      self.connection = self.sock.accept()[0].makefile('rb') # File-like obj
      print(self.name + ': Connection successful')
    except:
      print(self.name + ': Unable to connect')

  def closeConnection(self):
    self.connection.close()
    self.sock.close()
    print(self.name + ': Connection closed\n')

  def run(self):
    self.openConnection()  # Initializing
    self.closeConnection() # Initializing
    global globalStop    
    global workFlag
    openFileTimeStamp = 0
    logPath = ''
    while (not globalStop):
      if self.connection.closed and workFlag: # If connection to video stream was closed
        self.openConnection()
      if workFlag == 0: # If no log writing
          if self.fileFlag: # If log file is opened
            closeFiles(self)
            self.closeConnection()
      elif workFlag == 1: # If log is need to write
        if (not self.fileFlag) and (not self.connection.closed): # If no opened log file and connection established
          try:
            logPath = 'logs/' + datetime.now().strftime('%2y%m%d') + '_' + datetime.now().strftime('%H%M%S') + '/'
            self.logFilePath = logPath + self.name + '.h264'
            if not os.path.exists(logPath):
              try:
                os.mkdir(logPath)
                print('Created directory: ', logPath)
              except:
                print(self.name, ': error creating log directory')
                continue
            self.logFileStream = open(self.logFilePath, 'wb') # Writing bytes of video stream
            openFileTimeStamp = TimestampMillisec64()
            self.fileFlag = 1
            print('Created file: ', self.logFilePath)
          except:
            print(self.name + ": Error creating file")
        elif self.fileFlag: # If log is need to write and log file is opened
          #if TimestampMillisec64() - openFileTimeStamp > 3000: # If age of log file is greater than 3 seconds
          #  closeFile(self)
          #  self.closeConnection()
          try:
            if not self.connection.closed: # If connection established
              data = self.connection.read(1024) # Get 1k of data
              if not data: # If data is invalid
                print('Bad data')
                closeFiles(self)
                self.closeConnection()
              else: # Data is valid
                self.logFileStream.write(data)
          except:
            print('except: ' + self.name)
            closeFiles(self)
            self.closeConnection()
            continue
    closeFiles(self)
    self.closeConnection()

def closeFiles(logThread):
  logThread.logFileStream.close()
  logThread.logFileStreamLimited.close()
  logThread.fileFlag = 0
  print('Files ' + logThread.logFilePath + ', ' + logThread.logFilePathLimited + ' closed')

def TimestampMillisec64():
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)%4294967295

def exitHandler(sig, frame): # Ctrl+C soft exit
  global globalStop
  globalStop = 1
  workFlag = 0

signal.signal(signal.SIGINT, exitHandler) # Ctrl+C handling


videoThread = videoInThread("videoIn", '', 8000)
senseHatThread = logWriteThread('SenseHat', evaParsers.senseHat, '', 8097, '<2sIfffffffff',
                                           'time;ax;ay;az;gyroX;gyroY;gyroZ;magnetX;magnetY;magnetZ',
                                           '')
lowLevelThread = logWriteThread('LowLevel', evaParsers.lowLevel, '', 8091, '<2shIffddfIBBBB', 
                                           'SteerGrad;GlobalSTATUS;heading_in;Odometer;Xinert;Yinert;SpeedNow;timestamp;AccelPedal;BrakePedal;AKPP_now;reserved',
                                           'time;vel;SW;dist;accel;brake;gearbox')
navigationThread = logWriteThread('Navigation', evaParsers.navigation, '', 8090, '<2sIfddfhhfI', 
                                           'GPSStat;Zutm;Xutm;Yutm;HDT_Heading;accX;accY;diffAge;timestamp',
                                           'time;Xutm;Yutm;heading;accX;accY;diffAge')
neuroThread = logWriteThread('NeuroNet', 3, '', 8096, '', 
                                           'X*100;Y*100;TTC*10;reserve;timestamp', 
                                           '')
radarFrontThread = logWriteThread('RadarFront', 4, '', 8071, '', 
                                           'ObjId;Long;Lat;Power;timestamp',
                                           '')
radarRightThread = logWriteThread('RadarRight', 4, '', 8072, '', 
                                           'ObjId;Long;Lat;Power;timestamp',
                                           '')
radarLeftThread = logWriteThread('RadarLeft', 4, '', 8073, '', 
                                           'ObjId;Long;Lat;Power;timestamp',
                                           '')
radarRearThread = logWriteThread('RadarRear', 4, '', 8074, '', 
                                           'ObjId;Long;Lat;Power;timestamp',
                                           '')

# Front 1
# Right 2
# Left 3
# Back 4

#videoThread.start()
senseHatThread.start()
lowLevelThread.start()
navigationThread.start()
#neuroThread.start()
#radarFrontThread.start()
#radarRightThread.start()
#radarLeftThread.start()
#radarRearThread.start()

while not globalStop:
  workFlag = evaParsers.getWorkFlag()
  sleep(0.01)

