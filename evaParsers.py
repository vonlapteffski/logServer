import struct

workFlag = 0

def getWorkFlag():
  global workFlag
  return workFlag

def setWorkFlag(value):
  global workFlag
  workFlag = value

def senseHat(rawData, packetFormat):
  unpackedData = struct.unpack(packetFormat, rawData)
  strData = str(unpackedData) # All data parser
  procData = strData[8:-1].replace(', ', ';') # Remove some symbols and replace
  return procData, ''


def navigation(rawData, packetFormat):
  unpackedData = struct.unpack(packetFormat, rawData) # All data coming from navigation
  unpackedDataLimited = (unpackedData[9], unpackedData[3], unpackedData[4], 
                                          unpackedData[5],unpackedData[6], unpackedData[7], unpackedData[8])
  strData = str(unpackedData) # All data parser
  procData = strData[8:-1].replace(', ', ';') # Remove some symbols and replace
  
  strData = str(unpackedDataLimited) # Limited data parser
  procDataLimited = strData[1:-1].replace(', ', ';') # Remove some symbols and replace
  
  return procData, procDataLimited

def lowLevel(rawData, packetFormat):
  global workFlag
  #print(rawData)
  unpackedData = struct.unpack(packetFormat, rawData) # All data coming from low level
  unpackedDataLimited = (unpackedData[8], unpackedData[7], unpackedData[1], unpackedData[4], # Limited data
                                          unpackedData[9], unpackedData[10], unpackedData[11])
  strData = str(unpackedData) # All data parser
  procData = strData[8:-1].replace(', ', ';') # Remove some symbols and replace

  strData = str(unpackedDataLimited) # Limited data parser
  procDataLimited = strData[1:-1].replace(', ', ';') # Remove some symbols and replace

  if int(unpackedData[11]) == 1:
    workFlag = 0
  else:
    workFlag = 1
  return procData, procDataLimited

def neuroNet(rawData, packetFormat):
  i = int(data[2])
  #timeStamp = TimestampMillisec64()
  for x in range(i):
    neuroBytes = data[-8:]
    data = data[:-8]
    unpackedData = struct.unpack('>hhhh', neuroBytes)
    strData = str(unpackedData)
    strData = strData.replace(', ', ';')[1:-1]
    procData = strData + ';' + str(timeStamp)
  return procData, procDataLimited

def radarParser(rawData, packetFormat):
  i = int(data[2])
  data = data[3:]
  for x in range(i):
    radarBytes = data[:22]
    data = data[22:]
    unpackedData = struct.unpack('<HfffLL', radarBytes)
    strData = str(unpackedData)
    strData = strData.replace(', ', ';')[1:-4]
  return procData

