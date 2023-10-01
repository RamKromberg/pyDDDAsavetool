#!/usr/bin/env python

#pyDDDAsavetool
#Dragon's Dogma: Dark Arisen save game unpacker
#https://github.com/RamKromberg/pyDDDAsavetool

#A class to handle DDDA save files.
#ported to python from [FluffyQuack's DDsavetool](http://www.fluffyquack.com/tools/source/DDsavetool.rar) as made available over at [Steam Community](https://steamcommunity.com/app/367500/discussions/8/451850849187495873/).

#DONE: Tested on GOG PC version for offline use.
#TODO: Steam, various consoles including the original big endian one etc...

#I'm not sure about the licensing situation but as far as I'm concerned you can use it as you'd like, no credits due.


from dataclasses import dataclass
import struct
import zlib

@dataclass
class DDDASaveHeader:
	"""DDDA save header"""
	version: int = None
	unCompressedSize: int = None
	compressedSize: int = None
	u1: int = 860693325
	u2: int = 0
	u3: int = 860700740
	hash: int = None #crc32 of compressed save data
	u4: int = 1079398965
	littleEndian = True
	headerLength = 32
	def __init__(self, rawHeader=None):
		if rawHeader != None:
			self.parse(rawHeader)
	def parse(self, rawHeader):
		if len(rawHeader) != self.headerLength:
			raise ValueError("parse requires a buffer of 32 bytes" % rawHeader)
		version, unCompressedSize, compressedSize, u1, u2, u3, hash, u4 = struct.unpack('< I I I I I I I I', rawHeader)
		if version != 21:
			#TODO: incomplete and untested
			version, unCompressedSize, compressedSize, u1, u2, u3, hash, u4 = struct.unpack('> I I I I I I I I', rawHeader)
			littleEndian = False
		if (u1 != self.u1 or u2 != self.u2 or u3 != self.u3 or u4 != self.u4):
			raise ValueError("Invalid DDDASaveHeader" % rawHeader)
		else:
			self.version, self.unCompressedSize, self.compressedSize, self.hash = version, unCompressedSize, compressedSize, hash
	def serialize(self):
		if self.littleEndian:
			stuct = struct.pack('< I I I I I I I I', self.version, self.unCompressedSize, self.compressedSize, self.u1, self.u2, self.u3, self.hash, self.u4)
		else:
			stuct = struct.pack('> I I I I I I I I', self.version, self.unCompressedSize, self.compressedSize, self.u1, self.u2, self.u3, self.hash, self.u4)
		return stuct
	def __getitem__(self, item):
		if self.littleEndian:
			match item:
				case 0:
					return self.version
				case 1:
					return self.unCompressedSize
				case 2:
					return self.compressedSize
				case 3:
					return self.u1
				case 4:
					return self.u2
				case 5:
					return self.u3
				case 6:
					return self.hash
				case 7:
					return self.u4
				case int():
					raise IndexError("index \"%s\" out of range" % item)
				case str():
					try:
						return getattr(self, item)
					except:
						raise KeyError ("key \"%s\" out of range" % item)
				case _:
					raise TypeError('Unsupported type' % item)
		else:
			match item:
				case 0:
					return self.u4
				case 1:
					return self.hash
				case 2:
					return self.u3
				case 3:
					return self.u2
				case 4:
					return self.u1
				case 5:
					return self.compressedSize
				case 6:
					return self.unCompressedSize
				case 7:
					return self.version
				case int():
					raise IndexError("index \"%s\" out of range" % item)
				case str():
					try:
						return getattr(self, item)
					except:
						raise KeyError ("key \"%s\" out of range" % item)
				case _:
					raise TypeError('Unsupported type' % item)
	def __str__(self):
		if self.version == 21:
			return "Dragon's Dogma: Dark Arisen save header"
		elif self.version == 5:
			return "Dragon's Dogma original console save header"
		else:
			return str(type(self))

class DDDASave:
	header = DDDASaveHeader()
	data = None
	fileLength = 524288
	def __init__(self, buffer=None):
		if buffer != None:
			peek=buffer.peek(1)[0]
			match peek:
				case 21:
					self.openSav(buffer)
				case 5:
					#TODO: untested
					self.openSav(buffer)
				case 60:
					self.openXml(buffer)
				case _:
					raise ValueError ("magick byte %s unsupported" % peek)
	def openSav(self, buffer):
		self.header.parse(buffer.read(self.header.headerLength))
		data_compressed = buffer.read(self.fileLength-self.header.headerLength)
		self.data = zlib.decompress(data_compressed)
	def openXml(self, buffer):
		self.data = buffer.read()
		self.header.version = 21
	def compress(self, data=None):
		data = self.data if data==None else data
		return zlib.compress(data, 3) #h78 h5E = b01111000 = zlib level 4
	def checksum(self, data_compressed=None):
		data_compressed = self.compress() if data_compressed==None else data_compressed
		hash = (zlib.crc32(data_compressed) ^ -1) % (1<<32)
		return hash
	def checksize(self, data_compressed=None):
		data_compressed = self.compress() if data_compressed==None else data_compressed
		data_compressed_size = len(data_compressed)
		return data_compressed_size
	def unpack(self, data=None):
		#xml output
		data = self.data if data==None else data
		return data.decode('utf-8')
	def __str__(self, data=None):
		data = self.data if data==None else data
		return self.unpack(data)
	def convert(self, data=None):
		#TODO: endian and pc-to-console-to-pc stuff...
		data = self.data if data==None else data
		if data.decode('utf-8')[-9:] == "</class>\n":
			print("PC save")
	def pack(self, data=None):
		#compress the new data
		data_compressed = self.compress() if data==None else self.compress(data)
		#update the header
		self.header.unCompressedSize = len(self.data) if data==None else len(data)
		self.header.compressedSize = self.checksize(data_compressed)
		self.header.hash = self.checksum(data_compressed)
		#put the updated header and compressed data together in a pre-padded bytearray and return it for write out
		compBuffer = bytearray(b'\0' * self.fileLength)
		for i, c in enumerate(self.header.serialize()):
			compBuffer[i] = c
		for i, c in enumerate(data_compressed):
			compBuffer[i+32] = c
		return(compBuffer)

def main():
	#usage example 1/2 for DDDASave
	#open existing save
	f = open("DDDA.sav","rb")
	save = DDDASave(f)
	f.close()
	#unpack the xml
	f=open("DDDA.sav.xml",'w')
	f.write(save.unpack())
	f.close
	#repack the packed save
	#note no recompression and re-hashing were performed so the output is identical to the input
	f=open("backup_DDDA.sav",'wb')
	f.write(save.pack())
	f.close()

	#usage example 2/2 for DDDASave
	#pack existing xml
	#note: Even though zlib routines vary between libraries so the resulting files and headers from DDDA, easyzlib (as used by FluffyQuack's DDSaveTool) and python's zlib (as used here) all differ, decompression remains is unaffected.
	f=open("DDDA.sav.xml",'rb')
	save = DDDASave(f)
	f.close()
	f=open("new_DDDA.sav",'wb')
	f.write(save.pack())
	f.close()

if __name__ == '__main__':
	main()
