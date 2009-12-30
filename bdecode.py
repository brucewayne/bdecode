#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os.path, glob, datetime
from string import Template
import cStringIO, binascii, hashlib
import psyco
from struct import *
from array import array
import re
import ntpath

# Requirement
try:
	from bencode import bdecode
	from bencode import bencode
except ImportError:
	try:
		from BitTorrent.bencode import bdecode
	except ImportError:
		sys.stderr.write("%s: ERROR: Missing dependency\nbencode.py was not found in current directory or in local BitTorrent Client (Mainline) installation.\n" % sys.argv[0])
		sys.stderr.flush()
		sys.exit(1)

def parse_resume(resume):
	f = open(resume,'rb')
	t_dict = bdecode(f.read())
	f.close()
	try:
		print 'Fileguard =', t_dict['.fileguard']
		del t_dict['.fileguard']
	except:
		print 'No fileguard found!'
	return t_dict
def show_jobname(t_dict):
	for key in t_dict.keys():
		print key
def find_jobname(t_dict, jobname):
	for key in t_dict.keys():
		if key.find(jobname) != -1:
			return key
def get_jobstatus(job):
	completed = []
	have = job['have']
#	bitmask = [128,64,32,16,8,4,2,1]
	bitmask = [1,2,4,8,16,32,64,128]
	for bytenum in xrange(0,len(have)):
		byte = unpack('B', have[bytenum])
		for bit in xrange(0,8):
			if byte[0] & bitmask[bit]:
				completed.append( (bytenum * 8) + bit )
	return completed
def save_jobstatus(jobname, jobstatus):
	jobstatus_file = open(jobname + '.job', 'wb')
	h_array = array('H', jobstatus)
	h_array.tofile(jobstatus_file)
	jobstatus_file.close()
def read_jobstatus(jobname):
	jobstatus_file = open(jobname + '.job', 'rb')
	h_array = array('H')
	h_array.fromstring( jobstatus_file.read() )
	jobstatus_file.close()
	return h_array.tolist()
def get_fileguard(t_dict):
	fg = hashlib.sha1( bencode(t_dict) ).hexdigest()
	return fg.upper()
def parse_torrent(path):
	torrentfile = open( path )
	torrent = bdecode(torrentfile.read())
	torrentfile.close()
	return torrent
def get_start_total(torrent, t_chunk_len, filename):
	startpiece = 0
	try:		
		for tfile in torrent['info']['files']:
			if tfile['path'][0] == filename:
				filepos = startpiece
				startpiece = int(startpiece / t_chunk_len)
				file_pieces = tfile['length'] / t_chunk_len
				break
			startpiece += tfile['length']
	except:
		file_pieces = torrent['info']['length'] / t_chunk_len
		filepos = startpiece
	return startpiece, file_pieces, filepos
def get_have(list, havelen):
	bitmask = [1,2,4,8,16,32,64,128]
	piece = list.pop()
	bitmap = cStringIO.StringIO()
	for bytenum in xrange(0, havelen):
#		print bytenum, piece
		byte = 0
		for bit in xrange(0,8):
			if piece == (bytenum*8) + bit:
				try:
					piece = list.pop()
				except:
					piece = -1
				byte = byte | bitmask[bit]
				#print byte
#		print 'Byte 2', byte
		bitmap.write( chr(byte) )
	have = bitmap.getvalue()
	bitmap.close()
	return have
def guess_encoding(text):
	encodings = ['big5', 'gb2312', 'gb18030', 'utf-8', 'ascii']
	for best_enc in encodings:
		try:
			unicode(text,best_enc,"strict")
		except:
			pass
		else:
			break
		return best_enc 
def show_files(torrent):
	encodings = [ 'ascii', 'us-ascii', 'utf-8', 'big5', 'gb2312', 'gb18030' ]
	try:
		for enc in encodings:
			filenames = ''
			for tfile in torrent['info']['files']:
				filenames = filenames + tfile['path'][0] + '\n'
			try:
				print unicode(filenames, enc).encode('utf-8')
				#~ enc_res = str( raw_input('Encoding is %s? (Y/n)' % enc) )
				#~ if enc_res in ('Y', 'y', 'yes'):
				return enc
			except:
				pass
	except:
		for enc in encodings:
			filename = torrent['info']['name']
			try:
				print unicode(filename, enc).encode('utf-8')
				#~ enc_res = str( raw_input('Encoding is %s? (Y/n)' % enc) )
				#~ if enc_res in ('Y', 'y', 'yes', ''):
				return enc
			except:
				pass

def create_file(jobname):
	t_dict1 = parse_resume(sys.argv[1])
	jobname1 = find_jobname(t_dict1, jobname)
	t_dict2 = parse_resume(sys.argv[2])
	jobname2 = find_jobname(t_dict2, jobname)
	path1 = re.sub( '^[Zz]:', '/media/hda7', re.sub( r'\\', '/', t_dict1[jobname1]['path'] ) )
	tpath1 =  re.sub( '^[Cc]:', '/home/kira/.wine/drive_c', re.sub( r'\\', '/', jobname1 ) )	
	path2 = re.sub( '^[Zz]:', '/media/hda7', re.sub( r'\\', '/', t_dict2[jobname2]['path'] ) )
	print path1, path2

	torrent = parse_torrent(tpath1)
	t_chunk_len = torrent['info']['piece length']

	show_files(torrent)
	filename = raw_input('Which file: ')
	(startpiece, file_pieces, filepos) = get_start_total(torrent, t_chunk_len, filename)
	print t_chunk_len, startpiece, file_pieces
	print 'File start pos = ', filepos
#	exit()

	infile1 = open(path1 + '/' + filename, 'rb')
	infile2 = open(path2 + '/' + filename, 'rb')
	outfilepath = raw_input('Save to: ')
	outfile = open(outfilepath + filename,'wb')
	digest_size = 20
	sha1 = cStringIO.StringIO()
	sha1.write(torrent['info']['pieces'])
	sha1.flush()
	sha1.seek( (startpiece+1) * digest_size)
	chunk1 = infile1.read( t_chunk_len - (filepos % t_chunk_len) )
	outfile.write(chunk1)
	for piecenum in xrange(startpiece, file_pieces + startpiece + 1):
		chunk_sha1 = sha1.read(digest_size)
		chunk = infile1.read(t_chunk_len)
		if hashlib.sha1(chunk).digest() == chunk_sha1:
			#print 'Piece', piecenum + 1
			outfile.seek( (t_chunk_len - (filepos % t_chunk_len) ) + (piecenum * t_chunk_len) )
			outfile.write(chunk)
		else:
			infile2.seek( (t_chunk_len - (filepos % t_chunk_len) ) + (piecenum * t_chunk_len) )
			chunk = infile2.read(t_chunk_len)
			if hashlib.sha1(chunk).digest() == chunk_sha1:
				#print 'Piece', piecenum + 1, 'from file2'
				outfile.seek( (t_chunk_len - (filepos % t_chunk_len) ) + (piecenum * t_chunk_len) )
				outfile.write(chunk)
			else:
				print 'No match for piece', piecenum + 1
	sha1.close()	
	infile1.close()
	infile2.close()
	outfile.close()
def job_union(jobname):
	t_dict1 = parse_resume(sys.argv[1])
	jobname1 = find_jobname(t_dict1, jobname)
	list1 = get_jobstatus(t_dict1[jobname1])
	t_dict2 = parse_resume(sys.argv[2])
	jobname2 = find_jobname(t_dict2, jobname)
	list2 = get_jobstatus(t_dict2[jobname2])
	unionlist = list( set(list1).union(set(list2)) )
	unionlist.sort()
	unionlist.reverse()
	print 'List 1 -', len(list1), '/', len( t_dict1[jobname1]['have'] )
	print 'List 2 -', len(list2), '/', len( t_dict2[jobname2]['have'] )
	print 'Union -', len(unionlist)
#	print unionlist
#	exit()

	t_dict1[jobname1]['have'] = get_have(unionlist, len(t_dict1[jobname1]['have']) )

	fg = get_fileguard(t_dict1)
	print 'New fileguard -', fg
	t_dict1['.fileguard'] = fg
	resume_file = open(jobname + '_resume_union', 'wb')
	resume_file.write(bencode(t_dict1))
	resume_file.flush()
	resume_file.close()
def job_split(jobname):
	t_dict1 = parse_resume(sys.argv[1])
	jobname1 = find_jobname(t_dict1, jobname)
	list1 = get_jobstatus(t_dict1[jobname1])
	(progdir, fileName) = os.path.split(sys.argv[1])
	(tdir, tName) = ntpath.split(jobname1)
	tpath1 =  progdir + '/' + tName

	torrent = parse_torrent(tpath1)
	t_chunk_len = torrent['info']['piece length']
	enc = show_files(torrent)
	utf_filename = raw_input('Which file: ')
	filename = unicode(utf_filename, 'utf-8').encode(enc)
#	print filename

	(startpiece, file_pieces, filepos) = get_start_total(torrent, t_chunk_len, filename)

	startpercent = int( raw_input('Start at what percent: ') )
	stoppercent = int( raw_input('End at what percent: ') )

	fill = str ( raw_input('Fill? (Y/n)') )
	if fill in ('Y', 'y', 'yes', ''):
		start = startpiece + int(file_pieces * startpercent / 100)
		end = startpiece + int(file_pieces * stoppercent / 100)
		for x in xrange(start, end):
			list1.append(x)
	else:
		start = int( file_pieces * startpercent / 100 )
		end = int( file_pieces * stoppercent / 100 )
		for x in xrange( start, end ):
			list1.remove(x)
	list1 = list( set(list1) )
	list1.sort()
	list1.reverse()
	print 'List 1 -', len(list1), '/', file_pieces
#	print list1
#	exit()

	t_dict1[jobname1]['have'] = get_have(list1, len(t_dict1[jobname1]['have']) )

	fg = get_fileguard(t_dict1)
	print 'New fileguard -', fg
	t_dict1['.fileguard'] = fg
	resume_file = open(progdir + '/' + jobname + '_resume', 'wb')
	resume_file.write(bencode(t_dict1))
#	resume_file.flush()
	resume_file.close()
	resume_swap = str ( raw_input('Want to backup and overwrite resume.dat? (Y/n)') )
	if resume_swap in ('Y', 'y', 'yes', ''):
		os.rename( progdir + '/resume.dat', progdir + '/resume.dat2' )
		os.rename( progdir + '/' + jobname + '_resume', progdir + '/resume.dat')

t_dict = parse_resume(sys.argv[1])
show_jobname(t_dict)
jobname = raw_input('Which job: ')
#torrent = parse_torrent( '/home/kira/.wine/drive_c/Program Files/utorrent161/' + jobname )
#show_files(torrent)
#~ job_union(jobname)
job_split(jobname)
#~ create_file(jobname)
exit()
#print find_jobname(t_dict, jobname)
jobstatus = get_jobstatus(t_dict[jobname])
print jobname, jobstatus
#save_jobstatus(jobname, jobstatus)
#oldjobstatus = read_jobstatus(jobname)
#print oldjobstatus
#print jobstatus