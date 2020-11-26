#!/usr/bin/env python3

import argparse
import time
from picamera import PiCamera, Color
from aiy.vision.inference import CameraInference
from aiy.vision.models import face_detection
from aiy.vision.annotator import Annotator
from aiy.vision.models import image_classification
from aiy.leds import Leds, Color
from aiy.board import Board, Led
from aiy.toneplayer import Note
from aiy.trackplayer import NoteOff, Arpeggio, StopPlaying, TrackPlayer, TrackLoader




ticks = time.time()
alertLoader = TrackLoader(22,"sadtrombone.track")   #the gpio, input the file name for the track
finalLoader = TrackLoader(22, "congratulations.track")
alertPlayer = alertLoader.load()
finalPlayer = finalLoader.load()

def durationOver(x):
	pomodoro = x #25 mins (used for attention span) - initially using 20 seconds for testing
	cur_ticks = time.time()
	if (cur_ticks-ticks)<pomodoro:
		return True
	return False

#Image classification main
def classes_info(classes):
	return ', '.join('%s (%.2f)' % pair for pair in classes)

def face_detection_inference(camera,args):
	"""Face detection camera inference example."""

	with CameraInference(face_detection.model()) as inference:
		cam_tick = time.time()
		for result in inference.run(args.num_frames):
			time_passed = time.time() - cam_tick
			if time_passed>2:
				print("Your Face is not detected !!")
				return False
			faces = face_detection.get_faces(result)
			print('#%05d (%5.2f fps): num_faces=%d' %(inference.count, inference.rate, len(faces)))
			camera.annotate_text = 'Number of Faces detected ' + str(len(faces))
			if len(faces) > 0:
				return True
		return False

def image_calssification_inference(camera,args):
	with CameraInference(image_classification.model()) as inference:
		cam_tick = time.time()
		for result in inference.run(args.num_frames):
			time_passed = time.time() - cam_tick
			if time_passed>2:
				#No Phone detected and the checker timed out
				return False
			#return the classes as an array of tuple (pairs)
			classes = image_classification.get_classes(result, top_k=args.num_objects)
			print(classes_info(classes))
			for pair in classes:
				x,y = pair
				#check for the threshold first
				if x == "iPod" or x== "laptop/laptop computer" or x == "notebook/notebook computer" or x== "cellular telephone/cellular phone/cellphone/cell/mobile phone" or x == "hand-held computer/hand-held microcomputer":
					print("Phone detected !! please leave your phone and focus")
					return True
			#iPod,laptop/laptop computer, notebook/notebook computer, cellular telephone/cellular phone/cellphone/cell/mobile phone, hand-held computer/hand-held microcomputer
			if classes:
				camera.annotate_text = '%s (%.2f)' % classes[0]
		return False

def not_focus(model, count):
	if count > 4:
		with Leds() as leds:
			leds.update(Leds.rgb_on(Color.RED))
			print("You haven't been focusing for " + str(count) + " itrs ( " + model + " ), Take a break and return later")
			#Buzzer aleart
			time.sleep(5)
			leds.update(Leds.rgb_off())

def alertaction():
	with Leds() as leds:
			leds.update(Leds.rgb_on(Color.RED))
			print("Please Focus in your studies!!")
			alertPlayer.play()
			leds.update(Leds.rgb_off())




#Face detection main
def main():

	print('LED is ON while button is pressed (Ctrl-C for exit).')
	with Board() as board:
		board.button.wait_for_press()
		print('ON')
		board.led.state = Led.ON
		board.button.wait_for_release()
		print('OFF')
		board.led.state = Led.OFF

	parserf = argparse.ArgumentParser()
	parserf.add_argument('--num_frames', '-n', type=int, dest='num_frames', default=None,
		help='Sets the number of frames to run for, otherwise runs forever.')
	argsf = parserf.parse_args()

	parser = argparse.ArgumentParser('Image classification camera inference example.')
	parser.add_argument('--num_frames', '-n', type=int, default=None,
		help='Sets the number of frames to run for, otherwise runs forever.')
	parser.add_argument('--num_objects', '-c', type=int, default=3,
		help='Sets the number of object interences to print.')
	parser.add_argument('--nopreview', dest='preview', action='store_false', default=True,
		help='Enable camera preview')
	args = parser.parse_args()

	# Forced sensor mode, 1640x1232, full FoV. See:
	# https://picamera.readthedocs.io/en/release-1.13/fov.html#sensor-modes
	# This is the resolution inference run on.
	with PiCamera(sensor_mode=4, resolution=(1640, 1232), framerate=30) as camera:
		camera.start_preview()
		camera.annotate_text_size = 60
		x = int(input("Please enter your study time in mins: "))		
		x =x*60
		phone_detct = 0
		no_face = 0
		if(face_detection_inference(camera,argsf)):
			print("Your face is detected turing Study mode on, Please try to focus for the upcoming " + str(x/60) +" mins" )
			while durationOver(x):
				time.sleep(5)
				found_phone = image_calssification_inference(camera,args)
				if found_phone:
					phone_detct +=1
					alertaction()
					#Stop the timer if not focusing for a long time
					not_focus("face", phone_detct)
				time.sleep(5)
				found_face = face_detection_inference(camera,argsf)
				if not found_face:
					no_face +=1
					alertaction()
					not_focus("phone", no_face)
				remtime = x- (time.time()-ticks)
				print(str(round(remtime/60, 2)) + " mins remaining")
				camera.annotate_text = str(round(remtime/60, 2)) + " mins remaining"

			finalPlayer.play()
			print("Congratutations, You have completed " + str(x/60) +" mins paying attention" )
			camera.annotate_text = "Congratutations, You have completed " + str(x/60) +" mins paying attention" 
			results = x-(5*(phone_detct + no_face))
			print("The effective study time is " + str(round (results/60, 2)) + " mins out of " + str(x/60) + " mins")
			print(str(round(5* no_face/60, 2)) + " mins was wasted because your face was not detected and " + str(round(5* phone_detct/60, 2)) + " mins was wasted because you were using your phone!!")
		else:
			print("ERROR: No face detected to start the timer for studying")
			camera.annotate_text = "ERROR: No face detected to start the timer for studying" 

		camera.stop_preview()


if __name__ == '__main__':
    main()
