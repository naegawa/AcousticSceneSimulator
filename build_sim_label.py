from SimMch.make_noise import make_white_noise
from SimMch.sim_tf import apply_tf
import SimMch.simmch
from SimMch.HARK_TF_Parser.read_mat import read_hark_tf
from SimMch.HARK_TF_Parser.read_param import read_hark_tf_param
import os
import sys
import numpy as np
import json
import math

if __name__ == "__main__":
	dataset_config={}
	## basic config
	fftLen = 512
	step = fftLen/4
	scale=32767.0
	output_dir="data_sim/"
	deg_step=30
	alpha=0.1
	f = open("setting.json")
	data = json.load(f)
	print data
	if len(sys.argv)<2:
		print >>sys.stderr,"[usage] python build_sim_dataset.py <tf.zip: transfer function file>"
		quit()
	tf_filename=sys.argv[1]
	enabled_wav_save=False
	## read tf 
	print "... reading", tf_filename
	tf_config=read_hark_tf(tf_filename)
	#mic_pos=read_hark_tf_param(tf_filename)
	#print "# mic positions  :",mic_pos
	
	dataset_wavname=[]
	dataset_wav=[]
	dataset_deg=[]
	for mic in data["mics"]:
		recorded_wav=[]
		for src in data["sources"]:
			m=np.array(mic["position"])
			s=np.array(src["position"])
			ch=0
			if "channel" in src:
				ch=int(src["channel"])
			start_time_sec=0
			if "start_time" in src:
				start_time_sec=float(src["start_time"])
			v = s-m
			theta=np.arctan2(v[1],v[0])-math.pi/2.0
			r= np.linalg.norm(m-s)
			print "r=",r
			print "theta=",theta
			wav_filename=src["file"]
			## read wav file
			print "... reading", wav_filename
			wav_data=SimMch.simmch.read_mch_wave(wav_filename)
			wav=wav_data["wav"]/scale
			fs=wav_data["framerate"]
			nch=wav_data["nchannels"]
			step_sec=step*1.0/fs
			if ch >= wav.shape[0]:
				print >>sys.stderr,"Error: ch=%d is out of range"%(ch)
				quit()
			mono_wavdata = wav[ch,:]
			src_theta=theta
			## apply TF
			src_index=SimMch.simmch.nearest_direction_index(tf_config,src_theta)
			if not src_index in tf_config["tf"]:
				print >>sys.stderr, "Error: tf index",src_index,"does not exist in TF file"
				quit()
			mch_wavdata=apply_tf(mono_wavdata,fftLen, step,tf_config,src_index)
			a=np.max(mch_wavdata)
			mch_wavdata=mch_wavdata/a
			print "# simulation: %s, direction of arrival: %f"%(wav_filename,theta)
			#
			print "# wav data :",mch_wavdata.shape
			padding_length=int(np.round(start_time_sec/step_sec))
			print "# padding samples: ",padding_length
			padding=np.zeros((mch_wavdata.shape[0],padding_length),dtype='float')
			mch_wavdata_with_padding=np.c_[mch_wavdata,padding]
			#
			recorded_wav.append(mch_wavdata_with_padding)
		##
		if(len(recorded_wav)>0):
			nch=recorded_wav[0].shape[0]
			wav_len=np.max([x.shape[1] for x in recorded_wav])
			mix_wavdata=np.zeros((nch,wav_len),dtype="float")
			for w in recorded_wav:
				l=w.shape[1]
				mix_wavdata[:,:l]+=w
			a=np.max(mix_wavdata)
			mix_wavdata=mix_wavdata/a
			### make noise
			nsamples=wav_len
			length=((nsamples-(fftLen-step))-1)/step+1
			mch_noise=make_white_noise(nch,length,fftLen,step)
			a=np.max(mch_noise)
			mch_noise=mch_noise/a

			## mix noise and m-ch wav
			mix_wavdata=mix_wavdata*(1-alpha)+mch_noise[:,:wav_len]*alpha
			## save
			output_filename="./data_sim/test"+mic["name"]+".wav"
			print "[SAVE]",output_filename
			SimMch.simmch.save_mch_wave(mix_wavdata*scale,output_filename)

