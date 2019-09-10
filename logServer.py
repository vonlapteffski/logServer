import socket
import threading
import struct
import signal
import os
from datetime import datetime

workFlag = 0
globalStop = 0

class logWriteThread (threading.Thread): # log writing thread (text data)
  def __init__(self, name, sensorID, ip, port, packetFormat, logFileHeader):
    threading.Thread.__init__(self)
    self.name = name # Name of thread
    self.sensorID = sensorID # ID of data sensor | Means: 1 - LowLevel Parser, 2 - Ordinary parser, 3 - Neuronet parser, 4 - Radar parser
    self.ip = ip # Ip to listen
    self.port = port # Port to listen
    self.packetFormat = packetFormat # String format to unpack struct
    self.logFileHeader = logFileHeader # Header of log .csv file
    self.fileFlag = 0 # Flag of opened log file

  def unpack(self, data):
    global workFlag
    procData = ''
    if self.sensorID == 1 or self.sensorID == 2:
      unpackedData = struct.unpack(self.packetFormat, data)
      strData = str(unpackedData)
      procData = strData[8:-1].replace(', ', ';') # Remove some symbols and replace
      procData = procData + ';'
      #print(procData)
      #print(data)
      # Only for low level device
      # |           |           |
      # V           V           V
      if self.sensorID == 1:
        if int(unpackedData[11]) == 1:
          workFlag = 0
        else:
          workFlag = 1
    elif self.sensorID == 3:
      i = int(data[2])
      timeStamp = TimestampMillisec64()
      for x in range(i):
        neuroBytes = data[-8:]
        data = data[:-8]
        unpackedData = struct.unpack('>hhhh', neuroBytes)
        strData = str(unpackedData)
        strData = strData.replace(', ', ';')[1:-1]
        procData = strData + ';' + str(timeStamp) + ';'
    elif self.sensorID == 4:
      i = int(data[2])
      #print(len(data), i)
      data = data[3:]
      for x in range(i):
        radarBytes = data[:22]
        #print(radarBytes)
        data = data[22:]
        unpackedData = struct.unpack('<HfffLL', radarBytes)
        strData = str(unpackedData)
        strData = strData.replace(', ', ';')[1:-4]
        procData = strData + ';'
        
    return procData

  def run(self):
    global globalStop
    global workFlag
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.settimeout(1)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    self.sock.bind((self.ip, self.port))
    openFileTimeStamp = 0
    logPath = 'logs/' + self.name + '/'
    while (not globalStop):
      try:
        data, addr = self.sock.recvfrom(1024)
        unpackedData = self.unpack(data)
        #print(unpackedData)
      except:
        continue
      if workFlag == 0: # If no log writing
          if self.fileFlag: # If log file is opened
            closeFile(self)
      elif workFlag == 1: # If log is need to write
        if (not self.fileFlag):
          try:
            self.logFilePath = logPath + datetime.now().strftime('%H%M%S') + '.csv'
            if not os.path.exists(logPath):
              try:
                os.mkdir(logPath)
                print('Created directory: ', logPath)
              except:
                print(self.name, ': error creating log directory')
                continue
            self.logFileStream = open(self.logFilePath, 'w')
            openFileTimeStamp = TimestampMillisec64()
            self.fileFlag = 1
            self.logFileStream.write(self.logFileHeader+'\n')
            print('Created file: ', self.logFilePath)
          except:
            print(self.name + ": Error creating file")
        elif self.fileFlag: # If log is need to write and log file is opened
          if TimestampMillisec64() - openFileTimeStamp > 900000: # If age of log file is greater than 15 minutes
            closeFile(self)
            continue
          try:
            self.logFileStream.write(str(unpackedData) + '\n')
          except:
            print('except: ' + self.name)
            closeFile(self)
            continue
    closeFile(self)
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
    logPath = 'logs/' + self.name + '/'
    while (not globalStop):
      if self.connection.closed and workFlag: # If connection to video stream was closed
        self.openConnection()
      if workFlag == 0: # If no log writing
          if self.fileFlag: # If log file is opened
            closeFile(self)
            self.closeConnection()
      elif workFlag == 1: # If log is need to write
        if (not self.fileFlag) and (not self.connection.closed): # If no opened log file and connection established
          try:
            # To do: makedir
            #self.logFile = './Logs/' + self.name + '/' + datetime.now().strftime('%d%m%Y') + '/' + datetime.now().strftime('%H%M') + '.h264'
            self.logFilePath = logPath + datetime.now().strftime('%H%M%S') + '.h264'
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
                closeFile(self)
                self.closeConnection()
              else: # Data is valid
                self.logFileStream.write(data)
          except:
            print('except: ' + self.name)
            closeFile(self)
            self.closeConnection()
            continue
    closeFile(self)
    self.closeConnection()

def closeFile(logThread):
  logThread.logFileStream.close()
  logThread.fileFlag = 0
  #workFlag = 0
  #globalStop = 1
  print('File ' + logThread.logFilePath + ' closed')

def TimestampMillisec64():
    return int((datetime.utcnow() - datetime(1970, 1, 1)).total_seconds() * 1000)%4294967295


def exitHandler(sig, frame): # Ctrl+C soft exit
  global globalStop
  globalStop = 1
  workFlag = 0

signal.signal(signal.SIGINT, exitHandler) # Ctrl+C handling


videoThread = videoInThread("videoIn", '', 8000)
senseHatThread = logWriteThread('SenseHat', 2, '', 8097, '<2sfffffffffI', 'accX;accY;accZ;gyroX;gyroY;gyroZ;magnetX;magnetY;magnetZ;timestamp;')
lowLevelThread = logWriteThread('LowLevel', 1, '', 8091, '<2sHIffddfIBBBB', 'Flags;GlobalSTATUS;SteerGrad*10;Odometer;Xinert;Yinert;SpeedNow;timestamp;AccelPedal;BrakePedal;AKPP_now;reserved;')
navigationThread = logWriteThread('Navigation', 2, '', 8090, '<2sIfddfhhfI', 'GPSStat;Zutm;Xutm;Yutm;HDT_Heading;CurrencyXmm;CurrencyYmm;diffAge;timestamp;')
neuroThread = logWriteThread('NeuroNet', 3, '', 8096, '', 'X*100;Y*100;TTC*10;reserve;timestamp;')
radarFrontThread = logWriteThread('RadarFront', 4, '', 8071, '', 'ObjId;Long;Lat;Power;timestamp;')
radarRightThread = logWriteThread('RadarRight', 4, '', 8072, '', 'ObjId;Long;Lat;Power;timestamp;')
radarLeftThread = logWriteThread('RadarLeft', 4, '', 8073, '', 'ObjId;Long;Lat;Power;timestamp;')
radarBackThread = logWriteThread('RadarBack', 4, '', 8074, '', 'ObjId;Long;Lat;Power;timestamp;')

# Front 1
# Right 2
# Left 3
# Back 4

videoThread.start()
senseHatThread.start()
lowLevelThread.start()
navigationThread.start()
neuroThread.start()
radarFrontThread.start()
radarRightThread.start()
radarLeftThread.start()
radarBackThread.start()
