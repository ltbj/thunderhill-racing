from MainNode.MainNode import MainNode
from ctypes import *
import array
from PIL import Image
from io import BytesIO
import numpy as np
from keras.models import load_model
import h5py
from keras import __version__ as keras_version
import tensorflow as tf
from keras import backend as K
from Preprocess import *
import cv2
import time
from data_buffer import DataBuffer
import queue
import threading


f = h5py.File("multiModel.h5", mode='r')
model_version = f.attrs.get('keras_version')
keras_version = str(keras_version).encode('utf8')

if model_version != keras_version:
	print('You are using Keras version ', keras_version, ', but the model was built using ', model_version)


def customLoss(y_true, y_pred):
	return K.mean(K.square(y_pred - y_true), axis=-1)

model = load_model("multiModel.h5", custom_objects={'customLoss':customLoss})
graph = tf.get_default_graph()

data_buffer = DataBuffer()
res_queue = queue.Queue(maxsize=1)

idxs = [0, 1, 2]
means = [-122.33790211, 39.53881540, 62.68238949]
stds = [0.00099555, 0.00180817, 13.48539298]


def normalize_vector(xVec):
	for i, mean, std in zip(idxs, means, stds):
		xVec[i] -= mean
		xVec[i] /= std
	return xVec


def copyImage(byte_array, imageSize):
	if imageSize > 8:
		resize(byte_array, imageSize)
		image = []
		for i in range(imageSize):
			image.append(byte_array[i])
		return array.array('B', image).tostring()
	return byte_array


def imageReceived(imageSize, rawImage, speed, lat, lon):
	print("in image received")
	print(speed, lat, lon)
	jpegImage = copyImage(rawImage, imageSize)
	data_buffer.add_item((jpegImage, speed, lat, lon))
	try:
		prediction = res_queue.get(block=False)
		Node.steerCommand(c_float(prediction[0]))
		Node.throttleCommand(c_float(prediction[1]))
		Node.brakeCommand(c_float(prediction[2]))
	except queue.Empty:
		pass


def make_prediction():
	global graph
	print('make prediction')
	while True:
		with graph.as_default():
			item = data_buffer.get_item_for_processing()
			if item and len(item) == 4:
				jpeg_image = item[0]
				speed = item[1]
				lat = item[2]
				lon = item[3]
				xVec = np.array([lon, lat, speed])
				norm_xVec = normalize_vector(xVec)
				if jpeg_image:
					image = Image.open(BytesIO(jpeg_image))
					image_array = np.asarray(image)
					image_array = cv2.resize(image_array, (320, 160))
					steering_angle, throttle, brake_value = model.predict([preprocessImage(image_array)[None,:,:,:], norm_xVec[None,:]])
					if res_queue.full(): # maintain a single most recent prediction in the queue
						res_queue.get(False)
					res_queue.put((steering_angle, throttle, brake_value))


thread = threading.Thread(target=make_prediction, args=())
thread.daemon = True
thread.start()


Node = MainNode(imageReceived)
Node.connectPolySync()
